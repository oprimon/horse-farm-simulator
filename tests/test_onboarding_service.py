"""Tests for `/start` onboarding flow service."""

from __future__ import annotations

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services import (
    choose_candidate_flow,
    name_horse_flow,
    start_onboarding_flow,
    view_candidates_flow,
)


def test_start_onboarding_flow_creates_session_for_new_player(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    generator_calls = 0

    def candidate_generator(seed: int | str | None):
        nonlocal generator_calls
        generator_calls += 1
        return [
            {"id": "A", "appearance_text": "Chestnut with a bright blaze", "hint": "Brave", "template_seed": 1},
            {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
            {"id": "C", "appearance_text": "Grey with a tiny star", "hint": "Curious", "template_seed": 3},
        ]

    result = start_onboarding_flow(
        repository=repository,
        user_id=111,
        guild_id=222,
        display_name="Mia",
        candidate_generator=candidate_generator,
    )

    assert generator_calls == 1
    assert result.already_adopted is False
    assert result.reused_active_session is False
    assert "/horse view" in result.message

    persisted = repository.get_player(user_id=111, guild_id=222)
    assert persisted is not None
    assert persisted["onboarding_session"]["active"] is True
    assert len(persisted["onboarding_session"]["candidates"]) == 3


def test_start_onboarding_flow_blocks_when_player_already_adopted(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with a bright blaze", "hint": "Brave", "template_seed": 11},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 12},
        {"id": "C", "appearance_text": "Grey with a tiny star", "hint": "Curious", "template_seed": 13},
    ]
    repository.start_onboarding(user_id=333, guild_id=444, candidates=candidates)
    repository.set_chosen_candidate(user_id=333, guild_id=444, candidate_id="A")
    repository.finalize_horse_name(user_id=333, guild_id=444, name="Luna")

    def should_not_run(seed: int | str | None):
        raise RuntimeError("Candidate generation should not run for adopted players")

    result = start_onboarding_flow(
        repository=repository,
        user_id=333,
        guild_id=444,
        display_name="Mia",
        candidate_generator=should_not_run,
    )

    assert result.already_adopted is True
    assert result.reused_active_session is False
    assert "already have a horse" in result.message


def test_start_onboarding_flow_is_idempotent_when_session_already_active(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    existing_candidates = [
        {"id": "A", "appearance_text": "Chestnut with a bright blaze", "hint": "Brave", "template_seed": 21},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 22},
        {"id": "C", "appearance_text": "Grey with a tiny star", "hint": "Curious", "template_seed": 23},
    ]
    repository.start_onboarding(user_id=555, guild_id=666, candidates=existing_candidates)

    generator_calls = 0

    def should_not_run(seed: int | str | None):
        nonlocal generator_calls
        generator_calls += 1
        return [
            {"id": "A", "appearance_text": "Black with dark stockings", "hint": "Steady", "template_seed": 31},
            {"id": "B", "appearance_text": "Dun with silver mane", "hint": "Bold", "template_seed": 32},
            {"id": "C", "appearance_text": "Pinto with broad snip", "hint": "Gentle", "template_seed": 33},
        ]

    result = start_onboarding_flow(
        repository=repository,
        user_id=555,
        guild_id=666,
        display_name="Mia",
        candidate_generator=should_not_run,
    )

    assert generator_calls == 0
    assert result.already_adopted is False
    assert result.reused_active_session is True
    assert "/horse view" in result.message

    persisted = repository.get_player(user_id=555, guild_id=666)
    assert persisted is not None
    assert persisted["onboarding_session"]["candidates"] == existing_candidates


def test_view_candidates_flow_fails_without_active_session(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = view_candidates_flow(
        repository=repository,
        user_id=777,
        guild_id=888,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_active_session is False
    assert result.already_adopted is False
    assert "No adoption session is active yet" in result.message
    assert "/start" in result.message


def test_view_candidates_flow_renders_candidate_payload(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=999, guild_id=111, candidates=candidates)

    result = view_candidates_flow(
        repository=repository,
        user_id=999,
        guild_id=111,
        display_name="Mia",
    )

    assert result.player is not None
    assert result.has_active_session is True
    assert result.already_adopted is False
    assert "A: Chestnut with bright blaze | Hint: Brave" in result.message
    assert "B: Bay with white socks | Hint: Calm" in result.message
    assert "C: Grey with tiny star | Hint: Curious" in result.message
    assert "/horse choose <id>" in result.message


def test_choose_candidate_flow_locks_valid_selection_and_persists(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=123, guild_id=456, candidates=candidates)

    result = choose_candidate_flow(
        repository=repository,
        user_id=123,
        guild_id=456,
        display_name="Mia",
        candidate_id="b",
    )

    assert result.invalid_candidate_id is False
    assert result.selection_locked is True
    assert result.selected_candidate_id == "B"
    assert "/horse name <name>" in result.message

    persisted = repository.get_player(user_id=123, guild_id=456)
    assert persisted is not None
    assert persisted["onboarding_session"]["chosen_candidate_id"] == "B"


def test_choose_candidate_flow_rejects_invalid_candidate_id(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=321, guild_id=654, candidates=candidates)

    result = choose_candidate_flow(
        repository=repository,
        user_id=321,
        guild_id=654,
        display_name="Mia",
        candidate_id="Z",
    )

    assert result.invalid_candidate_id is True
    assert result.selection_locked is False
    assert result.selected_candidate_id is None
    assert "Please choose A, B, or C" in result.message

    persisted = repository.get_player(user_id=321, guild_id=654)
    assert persisted is not None
    assert persisted["onboarding_session"]["chosen_candidate_id"] is None


def test_choose_candidate_flow_blocks_second_choice_when_locked(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=444, guild_id=555, candidates=candidates)
    repository.set_chosen_candidate(user_id=444, guild_id=555, candidate_id="A")

    result = choose_candidate_flow(
        repository=repository,
        user_id=444,
        guild_id=555,
        display_name="Mia",
        candidate_id="B",
    )

    assert result.invalid_candidate_id is False
    assert result.selection_locked is True
    assert result.selected_candidate_id == "A"
    assert "irreversible" in result.message

    persisted = repository.get_player(user_id=444, guild_id=555)
    assert persisted is not None
    assert persisted["onboarding_session"]["chosen_candidate_id"] == "A"


def test_name_horse_flow_rejects_name_length_boundaries(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=150, guild_id=250, candidates=candidates)
    repository.set_chosen_candidate(user_id=150, guild_id=250, candidate_id="A")

    too_short = name_horse_flow(
        repository=repository,
        user_id=150,
        guild_id=250,
        display_name="Mia",
        horse_name="A",
    )
    assert too_short.finalized is False
    assert too_short.invalid_name is True
    assert "between 2 and 20" in too_short.message

    too_long = name_horse_flow(
        repository=repository,
        user_id=150,
        guild_id=250,
        display_name="Mia",
        horse_name="A" * 21,
    )
    assert too_long.finalized is False
    assert too_long.invalid_name is True
    assert "between 2 and 20" in too_long.message


def test_name_horse_flow_rejects_profanity(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=151, guild_id=251, candidates=candidates)
    repository.set_chosen_candidate(user_id=151, guild_id=251, candidate_id="B")

    result = name_horse_flow(
        repository=repository,
        user_id=151,
        guild_id=251,
        display_name="Mia",
        horse_name="shit",
    )

    assert result.finalized is False
    assert result.invalid_name is True
    assert "cannot be used" in result.message

    persisted = repository.get_player(user_id=151, guild_id=251)
    assert persisted is not None
    assert persisted["adopted"] is False
    assert persisted["horse"] is None


def test_name_horse_flow_finalizes_adoption_and_blocks_repeated_naming(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=152, guild_id=252, candidates=candidates)
    repository.set_chosen_candidate(user_id=152, guild_id=252, candidate_id="C")

    result = name_horse_flow(
        repository=repository,
        user_id=152,
        guild_id=252,
        display_name="Mia",
        horse_name="  Luna  ",
    )

    assert result.finalized is True
    assert result.invalid_name is False
    assert "Luna is officially your horse now" in result.message
    assert "Grey with tiny star" in result.message
    assert "Curious" in result.message

    persisted = repository.get_player(user_id=152, guild_id=252)
    assert persisted is not None
    assert persisted["adopted"] is True
    assert persisted["horse"] is not None
    assert persisted["horse"]["name"] == "Luna"
    assert persisted["horse"]["appearance"] == "Grey with tiny star"
    assert persisted["horse"]["hint"] == "Curious"
    assert persisted["onboarding_session"]["active"] is False

    second_attempt = name_horse_flow(
        repository=repository,
        user_id=152,
        guild_id=252,
        display_name="Mia",
        horse_name="Nova",
    )
    assert second_attempt.finalized is False
    assert second_attempt.already_adopted is True
    assert "already adopted your horse" in second_attempt.message
