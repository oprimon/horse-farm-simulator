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
def test_stable_roster_flow_handles_empty_guild(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = stable_roster_flow(
        repository=repository,
        guild_id=700,
        display_name="Mia",
    )

    assert result.rows == []
    assert result.has_guild_context is True
    assert result.is_empty is True
    assert "No horses have been adopted here yet" in result.message
    assert "/start" in result.message


def test_stable_roster_flow_renders_sorted_rows_with_owner_display_names(tmp_path) -> None:
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
    owner_names = {501: "Mia", 502: "Rowan"}

    result = stable_roster_flow(
        repository=repository,
        guild_id=700,
        display_name="Mia",
        owner_display_name_resolver=lambda owner_user_id: owner_names.get(owner_user_id),
    )

    assert result.has_guild_context is True
    assert result.is_empty is False
    assert result.rows == [
        {
            "horse_id": 1,
            "horse_name": "Luna",
            "owner_user_id": 502,
            "owner_display_name": "Rowan",
            "guild_id": 700,
        },
        {
            "horse_id": 2,
            "horse_name": "Comet",
            "owner_user_id": 501,
            "owner_display_name": "Mia",
            "guild_id": 700,
        },
    ]
    assert "#1 | Luna | Owner: Rowan" in result.message
    assert "#2 | Comet | Owner: Mia" in result.message
    assert "Nova" not in result.message


