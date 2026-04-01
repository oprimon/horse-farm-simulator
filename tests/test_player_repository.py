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

    assert payload["schema_version"] == 2


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


def test_repository_migrates_mvp001_adopted_record_to_schema_v2(tmp_path):
    storage_path = tmp_path / "players.json"
    with storage_path.open("w", encoding="utf-8") as storage_file:
        json.dump(
            {
                "schema_version": 1,
                "players": {
                    "101:202": {
                        "user_id": 101,
                        "guild_id": 202,
                        "adopted": True,
                        "onboarding_session": {
                            "active": False,
                            "candidates": [],
                            "chosen_candidate_id": None,
                            "created_at": "2026-03-20T08:00:00+00:00",
                        },
                        "horse": {
                            "template_seed": 99,
                            "appearance": "Palomino",
                            "traits_visible": ["gentle"],
                            "hint": "Steady",
                            "name": "Luna",
                            "created_at": "2026-03-20T09:00:00+00:00",
                            "first_interaction_at": None,
                            "last_interaction_at": None,
                        },
                    }
                },
            },
            storage_file,
            indent=2,
        )

    repository = JsonPlayerRepository(storage_path=storage_path)
    migrated = repository.get_player(user_id=101, guild_id=202)

    assert migrated is not None
    horse = migrated["horse"]
    assert horse is not None
    assert horse["horse_id"] == 1
    assert horse["bond"] == 25
    assert horse["energy"] == 70
    assert horse["health"] == 75
    assert horse["confidence"] == 35
    assert horse["skill"] == 10
    assert horse["last_fed_at"] is None
    assert horse["last_groomed_at"] is None
    assert horse["last_rested_at"] is None
    assert horse["last_trained_at"] is None
    assert horse["last_rode_at"] is None
    assert horse["last_socialized_at"] is None
    assert horse["recent_activity"] is None

    repository.update_horse_state(
        user_id=101,
        guild_id=202,
        updates={
            "bond": 33,
            "energy": 120,
            "last_fed_at": "2026-03-20T10:00:00+00:00",
            "recent_activity": "Fed Luna after a calm walk.",
        },
    )

    with storage_path.open("r", encoding="utf-8") as storage_file:
        payload = json.load(storage_file)
    assert payload["schema_version"] == 2


def test_list_adopted_horses_by_guild_returns_sorted_scoped_rows(tmp_path):
    storage_path = tmp_path / "players.json"
    with storage_path.open("w", encoding="utf-8") as storage_file:
        json.dump(
            {
                "schema_version": 1,
                "players": {
                    "501:700": {
                        "user_id": 501,
                        "guild_id": 700,
                        "adopted": True,
                        "onboarding_session": {
                            "active": False,
                            "candidates": [],
                            "chosen_candidate_id": None,
                            "created_at": "2026-03-21T07:00:00+00:00",
                        },
                        "horse": {
                            "appearance": "Grey",
                            "hint": "Calm",
                            "name": "Comet",
                            "created_at": "2026-03-21T08:10:00+00:00",
                        },
                    },
                    "502:700": {
                        "user_id": 502,
                        "guild_id": 700,
                        "adopted": True,
                        "onboarding_session": {
                            "active": False,
                            "candidates": [],
                            "chosen_candidate_id": None,
                            "created_at": "2026-03-21T07:05:00+00:00",
                        },
                        "horse": {
                            "appearance": "Bay",
                            "hint": "Brave",
                            "name": "Luna",
                            "created_at": "2026-03-21T08:00:00+00:00",
                        },
                    },
                    "503:701": {
                        "user_id": 503,
                        "guild_id": 701,
                        "adopted": True,
                        "onboarding_session": {
                            "active": False,
                            "candidates": [],
                            "chosen_candidate_id": None,
                            "created_at": "2026-03-21T07:10:00+00:00",
                        },
                        "horse": {
                            "appearance": "Chestnut",
                            "hint": "Gentle",
                            "name": "Nova",
                            "created_at": "2026-03-21T08:20:00+00:00",
                        },
                    },
                },
            },
            storage_file,
            indent=2,
        )

    repository = JsonPlayerRepository(storage_path=storage_path)
    guild_rows = repository.list_adopted_horses_by_guild(guild_id=700)

    assert guild_rows == [
        {"horse_id": 1, "horse_name": "Luna", "owner_user_id": 502, "guild_id": 700},
        {"horse_id": 2, "horse_name": "Comet", "owner_user_id": 501, "guild_id": 700},
    ]

    other_guild_rows = repository.list_adopted_horses_by_guild(guild_id=701)
    assert other_guild_rows == [
        {"horse_id": 1, "horse_name": "Nova", "owner_user_id": 503, "guild_id": 701},
    ]


def test_update_two_horse_states_updates_both_players_in_one_save_cycle(tmp_path):
    storage_path = tmp_path / "players.json"
    repository = JsonPlayerRepository(storage_path=storage_path)
    candidates = [
        {"id": "A", "appearance_text": "Palomino", "hint": "Gentle", "template_seed": 99},
        {"id": "B", "appearance_text": "Dun", "hint": "Steady", "template_seed": 98},
        {"id": "C", "appearance_text": "Black", "hint": "Bold", "template_seed": 97},
    ]

    repository.start_onboarding(user_id=1, guild_id=700, candidates=candidates)
    repository.set_chosen_candidate(user_id=1, guild_id=700, candidate_id="A")
    repository.finalize_horse_name(user_id=1, guild_id=700, name="Nova")
    repository.start_onboarding(user_id=2, guild_id=700, candidates=candidates)
    repository.set_chosen_candidate(user_id=2, guild_id=700, candidate_id="B")
    repository.finalize_horse_name(user_id=2, guild_id=700, name="Luna")

    updated_a, updated_b = repository.update_two_horse_states(
        user_id=1,
        target_user_id=2,
        guild_id=700,
        updates={
            "bond": 28,
            "confidence": 36,
            "last_socialized_at": "2026-04-01T10:00:00+00:00",
            "recent_activity": "Nova had a playdate with Luna.",
        },
        target_updates={
            "bond": 27,
            "confidence": 37,
            "last_socialized_at": "2026-04-01T10:00:00+00:00",
            "recent_activity": "Luna had a playdate with Nova.",
        },
    )

    assert updated_a["horse"]["bond"] == 28
    assert updated_a["horse"]["confidence"] == 36
    assert updated_a["horse"]["last_socialized_at"] == "2026-04-01T10:00:00+00:00"
    assert updated_b["horse"]["bond"] == 27
    assert updated_b["horse"]["confidence"] == 37
    assert updated_b["horse"]["last_socialized_at"] == "2026-04-01T10:00:00+00:00"


def test_get_adopted_horse_by_id_resolves_owner_scoped_to_guild(tmp_path):
    storage_path = tmp_path / "players.json"
    with storage_path.open("w", encoding="utf-8") as storage_file:
        json.dump(
            {
                "schema_version": 2,
                "players": {
                    "11:700": {
                        "user_id": 11,
                        "guild_id": 700,
                        "adopted": True,
                        "onboarding_session": {
                            "active": False,
                            "candidates": [],
                            "chosen_candidate_id": None,
                            "created_at": None,
                        },
                        "horse": {
                            "horse_id": 1,
                            "name": "Nova",
                        },
                    },
                    "12:701": {
                        "user_id": 12,
                        "guild_id": 701,
                        "adopted": True,
                        "onboarding_session": {
                            "active": False,
                            "candidates": [],
                            "chosen_candidate_id": None,
                            "created_at": None,
                        },
                        "horse": {
                            "horse_id": 1,
                            "name": "Luna",
                        },
                    },
                },
            },
            storage_file,
            indent=2,
        )

    repository = JsonPlayerRepository(storage_path=storage_path)
    guild_row = repository.get_adopted_horse_by_id(guild_id=700, horse_id=1)
    missing_row = repository.get_adopted_horse_by_id(guild_id=700, horse_id=99)

    assert guild_row == {
        "horse_id": 1,
        "horse_name": "Nova",
        "owner_user_id": 11,
        "guild_id": 700,
    }
    assert missing_row is None
