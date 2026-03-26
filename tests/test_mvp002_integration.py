"""Integration-style tests for MVP-002 care, training, and first ride loop."""

from __future__ import annotations

import random

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services import (
    choose_candidate_flow,
    feed_horse_flow,
    groom_horse_flow,
    horse_profile_flow,
    name_horse_flow,
    ride_horse_flow,
    stable_roster_flow,
    start_onboarding_flow,
    train_horse_flow,
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


def _adopt_horse(
    repository: JsonPlayerRepository,
    *,
    user_id: int,
    guild_id: int,
    display_name: str,
    candidate_id: str,
    horse_name: str,
) -> None:
    start_result = start_onboarding_flow(
        repository=repository,
        user_id=user_id,
        guild_id=guild_id,
        display_name=display_name,
        candidate_generator=_fixed_candidates,
    )
    assert start_result.already_adopted is False

    choose_result = choose_candidate_flow(
        repository=repository,
        user_id=user_id,
        guild_id=guild_id,
        display_name=display_name,
        candidate_id=candidate_id,
    )
    assert choose_result.selection_locked is True

    name_result = name_horse_flow(
        repository=repository,
        user_id=user_id,
        guild_id=guild_id,
        display_name=display_name,
        horse_name=horse_name,
    )
    assert name_result.finalized is True


def test_mvp002_happy_path_care_to_train_to_ride_with_stable(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    _adopt_horse(
        repository,
        user_id=5101,
        guild_id=6101,
        display_name="Mia",
        candidate_id="A",
        horse_name="Luna",
    )
    _adopt_horse(
        repository,
        user_id=5102,
        guild_id=6101,
        display_name="Rowan",
        candidate_id="B",
        horse_name="Comet",
    )
    _adopt_horse(
        repository,
        user_id=5103,
        guild_id=6102,
        display_name="Ari",
        candidate_id="C",
        horse_name="Nova",
    )

    feed_result = feed_horse_flow(
        repository=repository,
        user_id=5101,
        guild_id=6101,
        display_name="Mia",
        d10_roll=lambda: 6,
    )
    assert feed_result.has_adopted_horse is True
    assert feed_result.energy_gain == 6

    groom_result = groom_horse_flow(
        repository=repository,
        user_id=5101,
        guild_id=6101,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: 94,
        d10_roll=lambda: 7,
    )
    assert groom_result.has_adopted_horse is True
    assert groom_result.groomed_stat == "bond"
    assert groom_result.stat_gain == 7

    train_d100_rolls = iter([95, 88, 10, 12])
    train_d10_rolls = iter([5, 4, 3])
    train_result = train_horse_flow(
        repository=repository,
        user_id=5101,
        guild_id=6101,
        display_name="Mia",
        d100_roll=lambda: next(train_d100_rolls),
        d10_roll=lambda: next(train_d10_rolls),
    )
    assert train_result.has_adopted_horse is True
    assert train_result.blocked_by_readiness is False
    assert train_result.skill_gain == 5
    assert train_result.confidence_gain == 4
    assert train_result.energy_cost == 3
    assert train_result.health_loss == 0

    ride_d100_rolls = iter([99, 5])
    ride_d10_rolls = iter([6, 2, 3, 4])
    ride_result = ride_horse_flow(
        repository=repository,
        user_id=5101,
        guild_id=6101,
        display_name="Mia",
        stat_selector=lambda: "confidence",
        d100_roll=lambda: next(ride_d100_rolls),
        d10_roll=lambda: next(ride_d10_rolls),
        rng=random.Random(42),
    )
    assert ride_result.has_adopted_horse is True
    assert ride_result.outcome is not None
    assert ride_result.ride_stat == "confidence"
    assert ride_result.ride_stat_gain == 6
    assert ride_result.energy_loss == 9
    assert ride_result.health_loss == 0

    profile_result = horse_profile_flow(
        repository=repository,
        user_id=5101,
        guild_id=6101,
        display_name="Mia",
    )
    assert profile_result.has_adopted_horse is True
    assert "Name: Luna" in profile_result.message
    assert ride_result.outcome.recent_activity_text in profile_result.message

    stable_result = stable_roster_flow(
        repository=repository,
        guild_id=6101,
        display_name="Mia",
        owner_display_name_resolver=lambda owner_id: {5101: "Mia", 5102: "Rowan"}.get(owner_id),
    )
    assert stable_result.is_empty is False
    assert stable_result.rows == [
        {
            "horse_id": 1,
            "horse_name": "Luna",
            "owner_user_id": 5101,
            "owner_display_name": "Mia",
            "guild_id": 6101,
        },
        {
            "horse_id": 2,
            "horse_name": "Comet",
            "owner_user_id": 5102,
            "owner_display_name": "Rowan",
            "guild_id": 6101,
        },
    ]
    assert "Nova" not in stable_result.message


def test_mvp002_failure_paths_before_adoption_and_train_refusal(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    pre_adoption_feed = feed_horse_flow(
        repository=repository,
        user_id=5201,
        guild_id=6201,
        display_name="Mia",
    )
    assert pre_adoption_feed.has_adopted_horse is False
    assert "There is no horse to feed yet" in pre_adoption_feed.message

    _adopt_horse(
        repository,
        user_id=5202,
        guild_id=6201,
        display_name="Mia",
        candidate_id="A",
        horse_name="Maple",
    )
    repository.update_horse_state(
        user_id=5202,
        guild_id=6201,
        updates={"energy": 24, "health": 80, "last_trained_at": None, "recent_activity": None},
    )

    train_result = train_horse_flow(
        repository=repository,
        user_id=5202,
        guild_id=6201,
        display_name="Mia",
    )
    assert train_result.has_adopted_horse is True
    assert train_result.blocked_by_readiness is True
    assert train_result.skill_gain == 0
    assert train_result.confidence_gain == 0
    assert train_result.energy_cost == 0
    assert train_result.health_loss == 0
    assert "/feed" in train_result.message
    assert "/rest" in train_result.message


def test_mvp002_persistence_survives_repository_reload(tmp_path) -> None:
    storage_path = tmp_path / "players.json"
    repository = JsonPlayerRepository(storage_path=storage_path)

    _adopt_horse(
        repository,
        user_id=5301,
        guild_id=6301,
        display_name="Mia",
        candidate_id="A",
        horse_name="Willow",
    )

    ride_d100_rolls = iter([99, 5])
    ride_d10_rolls = iter([8, 1, 1, 1])
    ride_result = ride_horse_flow(
        repository=repository,
        user_id=5301,
        guild_id=6301,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: next(ride_d100_rolls),
        d10_roll=lambda: next(ride_d10_rolls),
        rng=random.Random(3),
    )
    assert ride_result.has_adopted_horse is True
    assert ride_result.outcome is not None

    reloaded_repository = JsonPlayerRepository(storage_path=storage_path)
    persisted = reloaded_repository.get_player(user_id=5301, guild_id=6301)

    assert persisted is not None
    assert persisted["adopted"] is True
    assert persisted["horse"] is not None
    assert persisted["horse"]["name"] == "Willow"
    assert persisted["horse"]["last_rode_at"] is not None
    assert ride_result.outcome.recent_activity_text in persisted["horse"]["recent_activity"]
    assert "Ride notes:" in persisted["horse"]["recent_activity"]

    stable_result = stable_roster_flow(
        repository=reloaded_repository,
        guild_id=6301,
        display_name="Mia",
        owner_display_name_resolver=lambda owner_id: "Mia" if owner_id == 5301 else None,
    )
    assert stable_result.rows == [
        {
            "horse_id": 1,
            "horse_name": "Willow",
            "owner_user_id": 5301,
            "owner_display_name": "Mia",
            "guild_id": 6301,
        }
    ]
