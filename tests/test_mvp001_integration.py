"""Integration-style tests for MVP-001 onboarding and adoption journey."""

from __future__ import annotations

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services.lifecycle import (
    choose_candidate_flow,
    greet_horse_flow,
    horse_profile_flow,
    name_horse_flow,
    start_onboarding_flow,
    view_candidates_flow,
)


def _fixed_candidates(_seed: int | str | None):
    return [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Brave",
            "template_seed": 101,
            "traits_visible": ["steady", "kind"],
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 102,
            "traits_visible": ["careful", "curious"],
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Curious",
            "template_seed": 103,
            "traits_visible": ["gentle", "alert"],
        },
    ]


def test_mvp001_happy_path_full_onboarding_to_first_interaction(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    start_result = start_onboarding_flow(
        repository=repository,
        user_id=4001,
        guild_id=5001,
        display_name="Mia",
        candidate_generator=_fixed_candidates,
    )
    assert start_result.already_adopted is False
    assert "/horse view" in start_result.message
    assert start_result.presentation is not None
    assert start_result.presentation.title == "Welcome To Pferdehof"

    view_result = view_candidates_flow(
        repository=repository,
        user_id=4001,
        guild_id=5001,
        display_name="Mia",
    )
    assert view_result.has_active_session is True
    assert "A: Chestnut with bright blaze" in view_result.message
    assert view_result.presentation is not None
    assert view_result.presentation.title == "Your Horse Candidates"
    assert len(view_result.presentation.fields) == 3

    choose_result = choose_candidate_flow(
        repository=repository,
        user_id=4001,
        guild_id=5001,
        display_name="Mia",
        candidate_id="A",
    )
    assert choose_result.selection_locked is True
    assert choose_result.selected_candidate_id == "A"
    assert choose_result.presentation is not None
    assert choose_result.presentation.title == "Candidate Locked In"

    name_result = name_horse_flow(
        repository=repository,
        user_id=4001,
        guild_id=5001,
        display_name="Mia",
        horse_name="Luna",
    )
    assert name_result.finalized is True
    assert "Luna is officially your horse now" in name_result.message
    assert name_result.presentation is not None
    assert "Luna" in name_result.presentation.title

    horse_result = horse_profile_flow(
        repository=repository,
        user_id=4001,
        guild_id=5001,
        display_name="Mia",
    )
    assert horse_result.has_adopted_horse is True
    assert "Name: Luna" in horse_result.message
    assert horse_result.presentation is not None
    assert "Luna" in horse_result.presentation.title
    assert len(horse_result.presentation.fields) == 7

    greet_result = greet_horse_flow(
        repository=repository,
        user_id=4001,
        guild_id=5001,
        display_name="Mia",
    )
    assert greet_result.has_adopted_horse is True
    assert "You greet Luna softly" in greet_result.message
    assert greet_result.presentation is not None

    persisted = repository.get_player(user_id=4001, guild_id=5001)
    assert persisted is not None
    assert persisted["adopted"] is True
    assert persisted["horse"] is not None
    assert persisted["horse"]["name"] == "Luna"
    assert persisted["horse"]["first_interaction_at"] is not None


def test_mvp001_failure_choose_before_start(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = choose_candidate_flow(
        repository=repository,
        user_id=4101,
        guild_id=5101,
        display_name="Mia",
        candidate_id="A",
    )

    assert result.selection_locked is False
    assert result.has_active_session is False
    assert "No adoption session is active yet" in result.message


def test_mvp001_failure_name_before_choose(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    start_onboarding_flow(
        repository=repository,
        user_id=4201,
        guild_id=5201,
        display_name="Mia",
        candidate_generator=_fixed_candidates,
    )

    result = name_horse_flow(
        repository=repository,
        user_id=4201,
        guild_id=5201,
        display_name="Mia",
        horse_name="Luna",
    )

    assert result.finalized is False
    assert result.has_chosen_candidate is False
    assert "Choose your horse first" in result.message


def test_mvp001_failure_second_adoption_attempt_blocked(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    start_onboarding_flow(
        repository=repository,
        user_id=4301,
        guild_id=5301,
        display_name="Mia",
        candidate_generator=_fixed_candidates,
    )
    choose_candidate_flow(
        repository=repository,
        user_id=4301,
        guild_id=5301,
        display_name="Mia",
        candidate_id="A",
    )
    name_horse_flow(
        repository=repository,
        user_id=4301,
        guild_id=5301,
        display_name="Mia",
        horse_name="Luna",
    )

    second_start = start_onboarding_flow(
        repository=repository,
        user_id=4301,
        guild_id=5301,
        display_name="Mia",
        candidate_generator=_fixed_candidates,
    )

    assert second_start.already_adopted is True
    assert "already have a horse" in second_start.message
