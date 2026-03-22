"""Tests for JSON-backed player persistence."""

from __future__ import annotations

import json

import pytest

from pferdehof_bot.repositories import AdoptionConflictError, JsonPlayerRepository


def test_repository_crud_and_onboarding_flow(tmp_path):
    storage_path = tmp_path / "players.json"
    repository = JsonPlayerRepository(storage_path=storage_path)

    base_record = {
        "user_id": 101,
        "guild_id": 202,
        "adopted": False,
        "onboarding_session": {
            "active": False,
            "candidates": [],
            "chosen_candidate_id": None,
            "created_at": None,
        },
        "horse": None,
    }
    repository.upsert_player(base_record)

    loaded_player = repository.get_player(user_id=101, guild_id=202)
    assert loaded_player is not None
    assert loaded_player["user_id"] == 101
    assert loaded_player["adopted"] is False

    candidates = [
        {"id": "A", "appearance_text": "Chestnut with blaze", "hint": "Brave", "template_seed": 11},
        {"id": "B", "appearance_text": "Bay with socks", "hint": "Calm", "template_seed": 22},
        {"id": "C", "appearance_text": "Grey with star", "hint": "Curious", "template_seed": 33},
    ]

    player_after_start = repository.start_onboarding(
        user_id=101,
        guild_id=202,
        candidates=candidates,
        created_at="2026-03-22T10:00:00+00:00",
    )
    assert player_after_start["onboarding_session"]["active"] is True
    assert len(player_after_start["onboarding_session"]["candidates"]) == 3

    player_after_choose = repository.set_chosen_candidate(user_id=101, guild_id=202, candidate_id="B")
    assert player_after_choose["onboarding_session"]["chosen_candidate_id"] == "B"

    player_after_finalize = repository.finalize_horse_name(
        user_id=101,
        guild_id=202,
        name="Luna",
        created_at="2026-03-22T10:05:00+00:00",
    )
    assert player_after_finalize["adopted"] is True
    assert player_after_finalize["horse"]["name"] == "Luna"
    assert player_after_finalize["horse"]["appearance"] == "Bay with socks"
    assert player_after_finalize["onboarding_session"]["active"] is False

    with pytest.raises(AdoptionConflictError):
        repository.start_onboarding(user_id=101, guild_id=202, candidates=candidates)


def test_repository_persists_across_restart_and_has_schema_version(tmp_path):
    storage_path = tmp_path / "players.json"

    first_repository = JsonPlayerRepository(storage_path=storage_path)
    first_repository.start_onboarding(
        user_id=303,
        guild_id=404,
        candidates=[
            {"id": "A", "appearance_text": "Palomino", "hint": "Gentle", "template_seed": 99},
            {"id": "B", "appearance_text": "Dun", "hint": "Steady", "template_seed": 98},
            {"id": "C", "appearance_text": "Black", "hint": "Bold", "template_seed": 97},
        ],
        created_at="2026-03-22T12:00:00+00:00",
    )

    second_repository = JsonPlayerRepository(storage_path=storage_path)
    loaded_player = second_repository.get_player(user_id=303, guild_id=404)

    assert loaded_player is not None
    assert loaded_player["onboarding_session"]["active"] is True
    assert loaded_player["onboarding_session"]["created_at"] == "2026-03-22T12:00:00+00:00"

    with storage_path.open("r", encoding="utf-8") as storage_file:
        payload = json.load(storage_file)

    assert payload["schema_version"] == 1


def test_repository_records_first_and_repeat_horse_interactions(tmp_path):
    storage_path = tmp_path / "players.json"
    repository = JsonPlayerRepository(storage_path=storage_path)
    candidates = [
        {"id": "A", "appearance_text": "Palomino", "hint": "Gentle", "template_seed": 99},
        {"id": "B", "appearance_text": "Dun", "hint": "Steady", "template_seed": 98},
        {"id": "C", "appearance_text": "Black", "hint": "Bold", "template_seed": 97},
    ]
    repository.start_onboarding(user_id=505, guild_id=606, candidates=candidates)
    repository.set_chosen_candidate(user_id=505, guild_id=606, candidate_id="A")
    repository.finalize_horse_name(
        user_id=505,
        guild_id=606,
        name="Nova",
        created_at="2026-03-22T12:10:00+00:00",
    )

    first_player, is_first = repository.record_horse_interaction(
        user_id=505,
        guild_id=606,
        interacted_at="2026-03-22T12:15:00+00:00",
    )
    assert is_first is True
    assert first_player["horse"]["first_interaction_at"] == "2026-03-22T12:15:00+00:00"
    assert first_player["horse"]["last_interaction_at"] == "2026-03-22T12:15:00+00:00"

    second_player, is_second_first = repository.record_horse_interaction(
        user_id=505,
        guild_id=606,
        interacted_at="2026-03-22T12:20:00+00:00",
    )
    assert is_second_first is False
    assert second_player["horse"]["first_interaction_at"] == "2026-03-22T12:15:00+00:00"
    assert second_player["horse"]["last_interaction_at"] == "2026-03-22T12:20:00+00:00"
