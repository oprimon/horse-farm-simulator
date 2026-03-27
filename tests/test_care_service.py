"""Tests for `/start` onboarding flow service."""

from __future__ import annotations

import random
import json

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services import (
    admin_rename_horse_flow,
    choose_candidate_flow,
    feed_horse_flow,
    greet_horse_flow,
    groom_horse_flow,
    horse_profile_flow,
    name_horse_flow,
    rest_horse_flow,
    ride_horse_flow,
    stable_roster_flow,
    start_onboarding_flow,
    train_horse_flow,
    view_candidates_flow,
)


def _make_adopted_repo_for_rest(tmp_path, user_id: int = 930, guild_id: int = 931) -> JsonPlayerRepository:
    """Helper: create a repository with a fully adopted player."""
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Curious", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Brave", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=user_id, guild_id=guild_id, candidates=candidates)
    repository.set_chosen_candidate(user_id=user_id, guild_id=guild_id, candidate_id="A")
    repository.finalize_horse_name(user_id=user_id, guild_id=guild_id, name="Ember")
    return repository
def test_feed_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = feed_horse_flow(
        repository=repository,
        user_id=820,
        guild_id=821,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.energy_gain == 0
    assert "There is no horse to feed yet" in result.message
    assert "/start" in result.message


def test_feed_horse_flow_updates_energy_and_recent_activity(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Curious",
            "template_seed": 1,
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 2,
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Brave",
            "template_seed": 3,
        },
    ]
    repository.start_onboarding(user_id=822, guild_id=823, candidates=candidates)
    repository.set_chosen_candidate(user_id=822, guild_id=823, candidate_id="A")
    repository.finalize_horse_name(user_id=822, guild_id=823, name="Luna")
    repository.update_horse_state(
        user_id=822,
        guild_id=823,
        updates={"energy": 96},
    )

    result = feed_horse_flow(
        repository=repository,
        user_id=822,
        guild_id=823,
        display_name="Mia",
        d10_roll=lambda: 7,
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.energy_gain == 7
    assert "You offer a warm feed to Luna." in result.message
    assert "+7 energy" in result.message

    persisted = repository.get_player(user_id=822, guild_id=823)
    assert persisted is not None
    assert persisted["horse"]["energy"] == 100
    assert persisted["horse"]["last_fed_at"] is not None
    assert persisted["horse"]["recent_activity"] is not None
    assert "You fed Luna" in persisted["horse"]["recent_activity"]


def test_groom_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = groom_horse_flow(
        repository=repository,
        user_id=824,
        guild_id=825,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.groomed_stat is None
    assert result.stat_gain == 0
    assert "There is no horse to groom yet" in result.message
    assert "/start" in result.message


def test_groom_horse_flow_increases_selected_stat_when_check_passes(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Curious",
            "template_seed": 1,
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 2,
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Brave",
            "template_seed": 3,
        },
    ]
    repository.start_onboarding(user_id=826, guild_id=827, candidates=candidates)
    repository.set_chosen_candidate(user_id=826, guild_id=827, candidate_id="A")
    repository.finalize_horse_name(user_id=826, guild_id=827, name="Luna")
    repository.update_horse_state(
        user_id=826,
        guild_id=827,
        updates={"bond": 95},
    )

    result = groom_horse_flow(
        repository=repository,
        user_id=826,
        guild_id=827,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: 99,
        d10_roll=lambda: 8,
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.groomed_stat == "bond"
    assert result.stat_gain == 8
    assert "You groom Luna carefully." in result.message
    assert "+8 bond" in result.message

    persisted = repository.get_player(user_id=826, guild_id=827)
    assert persisted is not None
    assert persisted["horse"]["bond"] == 100
    assert persisted["horse"]["last_groomed_at"] is not None
    assert "You groomed Luna" in str(persisted["horse"]["recent_activity"])


def test_groom_horse_flow_keeps_selected_stat_when_check_fails(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Curious",
            "template_seed": 1,
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 2,
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Brave",
            "template_seed": 3,
        },
    ]
    repository.start_onboarding(user_id=828, guild_id=829, candidates=candidates)
    repository.set_chosen_candidate(user_id=828, guild_id=829, candidate_id="A")
    repository.finalize_horse_name(user_id=828, guild_id=829, name="Luna")
    repository.update_horse_state(
        user_id=828,
        guild_id=829,
        updates={"health": 88},
    )

    result = groom_horse_flow(
        repository=repository,
        user_id=828,
        guild_id=829,
        display_name="Mia",
        stat_selector=lambda: "health",
        d100_roll=lambda: 12,
        d10_roll=lambda: 10,
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.groomed_stat == "health"
    assert result.stat_gain == 0
    assert "quiet, comforting moment" in result.message

    persisted = repository.get_player(user_id=828, guild_id=829)
    assert persisted is not None
    assert persisted["horse"]["health"] == 88
    assert persisted["horse"]["last_groomed_at"] is not None


# ---------------------------------------------------------------------------
# T11 – admin_rename_horse_flow
# ---------------------------------------------------------------------------

def _make_adopted_repository(tmp_path, user_id: int = 900, guild_id: int = 901) -> JsonPlayerRepository:
    """Helper: create a repository with a fully adopted player."""
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=user_id, guild_id=guild_id, candidates=candidates)
    repository.set_chosen_candidate(user_id=user_id, guild_id=guild_id, candidate_id="A")
    repository.finalize_horse_name(user_id=user_id, guild_id=guild_id, name="Luna")
    return repository


def test_rest_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = rest_horse_flow(
        repository=repository,
        user_id=930,
        guild_id=931,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.health_gain == 0
    assert "There is no horse to rest yet" in result.message
    assert "/start" in result.message


def test_rest_horse_flow_updates_health_and_recent_activity(tmp_path) -> None:
    repository = _make_adopted_repo_for_rest(tmp_path, user_id=932, guild_id=933)
    repository.update_horse_state(
        user_id=932,
        guild_id=933,
        updates={"health": 88},
    )

    result = rest_horse_flow(
        repository=repository,
        user_id=932,
        guild_id=933,
        display_name="Mia",
        d10_roll=lambda: 6,
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.health_gain == 6
    assert "You settle Ember in for a comfortable rest." in result.message
    assert "+6 health" in result.message

    persisted = repository.get_player(user_id=932, guild_id=933)
    assert persisted is not None
    assert persisted["horse"]["health"] == 94
    assert persisted["horse"]["last_rested_at"] is not None
    assert "recent_activity" in persisted["horse"]
    assert "Ember rested quietly" in persisted["horse"]["recent_activity"]
    assert "+6 health" in persisted["horse"]["recent_activity"]


def test_rest_horse_flow_clamps_health_at_100(tmp_path) -> None:
    repository = _make_adopted_repo_for_rest(tmp_path, user_id=934, guild_id=935)
    repository.update_horse_state(
        user_id=934,
        guild_id=935,
        updates={"health": 97},
    )

    result = rest_horse_flow(
        repository=repository,
        user_id=934,
        guild_id=935,
        display_name="Mia",
        d10_roll=lambda: 10,
    )

    assert result.health_gain == 10
    persisted = repository.get_player(user_id=934, guild_id=935)
    assert persisted is not None
    assert persisted["horse"]["health"] == 100


def test_rest_horse_flow_returns_no_adopted_horse_for_unadopted_player(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Curious", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Brave", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=936, guild_id=937, candidates=candidates)

    result = rest_horse_flow(
        repository=repository,
        user_id=936,
        guild_id=937,
        display_name="Mia",
    )

    assert result.has_adopted_horse is False
    assert result.health_gain == 0
    assert "/start" in result.message


# ---------------------------------------------------------------------------
# T08 – train_horse_flow
# ---------------------------------------------------------------------------

def _make_adopted_repo_for_training(tmp_path, user_id: int = 940, guild_id: int = 941) -> JsonPlayerRepository:
    """Helper: create a repository with a fully adopted player."""
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Curious", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Brave", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=user_id, guild_id=guild_id, candidates=candidates)
    repository.set_chosen_candidate(user_id=user_id, guild_id=guild_id, candidate_id="A")
    repository.finalize_horse_name(user_id=user_id, guild_id=guild_id, name="Maple")
    return repository



