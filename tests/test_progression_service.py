"""Tests for `/start` onboarding flow service."""

from __future__ import annotations

import random
import json

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services.lifecycle import horse_profile_flow
from pferdehof_bot.services.progression import ride_horse_flow, train_horse_flow


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
def test_train_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = train_horse_flow(
        repository=repository,
        user_id=940,
        guild_id=941,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.blocked_by_readiness is False
    assert result.skill_gain == 0
    assert result.confidence_gain == 0
    assert result.energy_cost == 0
    assert result.health_loss == 0
    assert "There is no horse to train yet" in result.message
    assert "/start" in result.message


def test_train_horse_flow_refuses_when_energy_or_health_is_too_low(tmp_path) -> None:
    repository = _make_adopted_repo_for_training(tmp_path, user_id=942, guild_id=943)
    repository.update_horse_state(
        user_id=942,
        guild_id=943,
        updates={"energy": 9, "health": 80, "last_trained_at": None, "recent_activity": None},
    )

    result = train_horse_flow(
        repository=repository,
        user_id=942,
        guild_id=943,
        display_name="Mia",
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.blocked_by_readiness is True
    assert result.skill_gain == 0
    assert result.confidence_gain == 0
    assert result.energy_cost == 0
    assert result.health_loss == 0
    assert "hold off on training Maple" in result.message
    assert "/feed" in result.message
    assert "/rest" in result.message

    persisted = repository.get_player(user_id=942, guild_id=943)
    assert persisted is not None
    assert persisted["horse"]["energy"] == 9
    assert persisted["horse"]["last_trained_at"] is None
    assert persisted["horse"]["recent_activity"] is None


def test_train_horse_flow_updates_skill_confidence_and_energy(tmp_path) -> None:
    repository = _make_adopted_repo_for_training(tmp_path, user_id=944, guild_id=945)
    repository.update_horse_state(
        user_id=944,
        guild_id=945,
        updates={"skill": 20, "confidence": 30, "energy": 70, "health": 80},
    )
    d100_rolls = iter([87, 92, 14, 9])
    d10_rolls = iter([6, 4, 5])

    result = train_horse_flow(
        repository=repository,
        user_id=944,
        guild_id=945,
        display_name="Mia",
        d100_roll=lambda: next(d100_rolls),
        d10_roll=lambda: next(d10_rolls),
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.blocked_by_readiness is False
    assert result.skill_gain == 6
    assert result.confidence_gain == 4
    assert result.energy_cost == 5
    assert result.health_loss == 0
    assert "You guide Maple through a focused training session." in result.message
    assert "+6 skill, +4 confidence, -5 energy" in result.message
    assert "/ride" in result.message

    persisted = repository.get_player(user_id=944, guild_id=945)
    assert persisted is not None
    assert persisted["horse"]["skill"] == 26
    assert persisted["horse"]["confidence"] == 34
    assert persisted["horse"]["energy"] == 65
    assert persisted["horse"]["health"] == 80
    assert persisted["horse"]["last_trained_at"] is not None
    assert "You trained Maple" in str(persisted["horse"]["recent_activity"])
    assert "+6 skill" in str(persisted["horse"]["recent_activity"])
    assert "+4 confidence" in str(persisted["horse"]["recent_activity"])
    assert "-5 energy" in str(persisted["horse"]["recent_activity"])


def test_train_horse_flow_can_apply_slight_health_loss(tmp_path) -> None:
    repository = _make_adopted_repo_for_training(tmp_path, user_id=946, guild_id=947)
    repository.update_horse_state(
        user_id=946,
        guild_id=947,
        updates={"skill": 12, "confidence": 20, "energy": 50, "health": 8},
    )
    repository.update_horse_state(
        user_id=946,
        guild_id=947,
        updates={"health": 40},
    )
    d100_rolls = iter([10, 5, 91, 88])
    d10_rolls = iter([3, 7])

    result = train_horse_flow(
        repository=repository,
        user_id=946,
        guild_id=947,
        display_name="Mia",
        d100_roll=lambda: next(d100_rolls),
        d10_roll=lambda: next(d10_rolls),
    )

    assert result.blocked_by_readiness is False
    assert result.skill_gain == 0
    assert result.confidence_gain == 0
    assert result.energy_cost == 3
    assert result.health_loss == 7
    assert "-7 health" in result.message

    persisted = repository.get_player(user_id=946, guild_id=947)
    assert persisted is not None
    assert persisted["horse"]["energy"] == 47
    assert persisted["horse"]["health"] == 33
    assert "-7 health" in str(persisted["horse"]["recent_activity"])


# ---------------------------------------------------------------------------
# ride_horse_flow tests
# ---------------------------------------------------------------------------


def _make_adopted_repo_for_riding(tmp_path, user_id: int = 950, guild_id: int = 951) -> JsonPlayerRepository:
    """Helper: create a repository with a fully adopted player ready to ride."""
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


def test_ride_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = ride_horse_flow(
        repository=repository,
        user_id=950,
        guild_id=951,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.blocked_by_readiness is False
    assert result.outcome is None
    assert result.ride_stat is None
    assert result.ride_stat_gain == 0
    assert result.energy_loss == 0
    assert result.health_loss == 0
    assert "There is no horse to ride yet" in result.message
    assert "/start" in result.message


def test_ride_horse_flow_stat_gain_and_energy_loss_no_health_loss(tmp_path) -> None:
    """Confidence increases, energy drops by 3d10, health unaffected (skill check passes)."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=952, guild_id=953)
    repository.update_horse_state(
        user_id=952,
        guild_id=953,
        updates={"confidence": 20, "bond": 30, "skill": 50, "energy": 60, "health": 70},
    )

    # d100[0]=90 > confidence(20) → gain; d10[0]=5 → gain=5
    # d10[1]=4, d10[2]=3, d10[3]=2 → energy_loss=9
    # d100[1]=30 <= skill(50) → no health loss
    d100_iter = iter([90, 30])
    d10_iter = iter([5, 4, 3, 2])

    result = ride_horse_flow(
        repository=repository,
        user_id=952,
        guild_id=953,
        display_name="Mia",
        stat_selector=lambda: "confidence",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(42),
    )

    assert result.has_adopted_horse is True
    assert result.blocked_by_readiness is False
    assert result.ride_stat == "confidence"
    assert result.ride_stat_gain == 5
    assert result.energy_loss == 9
    assert result.health_loss == 0
    assert result.outcome is not None
    assert result.presentation is not None
    assert result.presentation.title == "Ride Complete"

    # Message contains outcome narrative and stat summary.
    assert "-9 energy" in result.message
    assert "+5 confidence" in result.message
    assert "/horse" in result.message

    persisted = repository.get_player(user_id=952, guild_id=953)
    assert persisted is not None
    assert persisted["horse"]["confidence"] == 25
    assert persisted["horse"]["energy"] == 51
    assert persisted["horse"]["health"] == 70
    assert persisted["horse"]["last_rode_at"] is not None
    assert persisted["horse"]["recent_activity"] is not None


def test_ride_horse_flow_no_stat_gain_with_health_loss(tmp_path) -> None:
    """Bond check fails (no gain), energy drops, health drops due to low skill."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=954, guild_id=955)
    repository.update_horse_state(
        user_id=954,
        guild_id=955,
        updates={"confidence": 20, "bond": 30, "skill": 10, "energy": 60, "health": 70},
    )

    # d100[0]=5 <= bond(30) → no gain, no d10 consumed for gain
    # d10[0]=4, d10[1]=3, d10[2]=2 → energy_loss=9
    # d100[1]=90 > skill(10) → health loss; d10[3]=7
    d100_iter = iter([5, 90])
    d10_iter = iter([4, 3, 2, 7])

    result = ride_horse_flow(
        repository=repository,
        user_id=954,
        guild_id=955,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(42),
    )

    assert result.has_adopted_horse is True
    assert result.blocked_by_readiness is False
    assert result.ride_stat == "bond"
    assert result.ride_stat_gain == 0
    assert result.energy_loss == 9
    assert result.health_loss == 7

    assert "-9 energy" in result.message
    assert "-7 health" in result.message
    assert "+0" not in result.message

    persisted = repository.get_player(user_id=954, guild_id=955)
    assert persisted is not None
    assert persisted["horse"]["bond"] == 30
    assert persisted["horse"]["energy"] == 51
    assert persisted["horse"]["health"] == 63
    assert persisted["horse"]["last_rode_at"] is not None


def test_ride_horse_flow_energy_clamped_to_zero(tmp_path) -> None:
    """Energy loss exceeding current energy clamps to 0."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=956, guild_id=957)
    repository.update_horse_state(
        user_id=956,
        guild_id=957,
        updates={"confidence": 20, "bond": 30, "skill": 80, "energy": 30, "health": 60},
    )

    # d100[0]=5 <= confidence(20) → no gain
    # d10[0]=10, d10[1]=10, d10[2]=10 → energy_loss=30
    # d100[1]=50 <= skill(80) → no health loss
    d100_iter = iter([5, 50])
    d10_iter = iter([10, 10, 10])

    result = ride_horse_flow(
        repository=repository,
        user_id=956,
        guild_id=957,
        display_name="Mia",
        stat_selector=lambda: "confidence",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(1),
    )

    assert result.blocked_by_readiness is False
    assert result.energy_loss == 30
    persisted = repository.get_player(user_id=956, guild_id=957)
    assert persisted is not None
    assert persisted["horse"]["energy"] == 0


def test_ride_horse_flow_bond_can_increase(tmp_path) -> None:
    """Bond is the selected stat and increases successfully."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=958, guild_id=959)
    repository.update_horse_state(
        user_id=958,
        guild_id=959,
        updates={"confidence": 50, "bond": 10, "skill": 80, "energy": 70, "health": 80},
    )

    # d100[0]=95 > bond(10) → gain; d10[0]=8
    # d10[1]=3, d10[2]=2, d10[3]=1 → energy_loss=6
    # d100[1]=40 <= skill(80) → no health loss
    d100_iter = iter([95, 40])
    d10_iter = iter([8, 3, 2, 1])

    result = ride_horse_flow(
        repository=repository,
        user_id=958,
        guild_id=959,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(7),
    )

    assert result.ride_stat == "bond"
    assert result.blocked_by_readiness is False
    assert result.ride_stat_gain == 8
    assert result.energy_loss == 6

    persisted = repository.get_player(user_id=958, guild_id=959)
    assert persisted is not None
    assert persisted["horse"]["bond"] == 18
    assert persisted["horse"]["energy"] == 64


def test_ride_horse_flow_recent_activity_is_outcome_text(tmp_path) -> None:
    """recent_activity starts with outcome text and appends roll-aware ride notes."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=960, guild_id=961)
    repository.update_horse_state(
        user_id=960,
        guild_id=961,
        updates={"confidence": 80, "bond": 80, "skill": 80, "energy": 90, "health": 90},
    )

    result = ride_horse_flow(
        repository=repository,
        user_id=960,
        guild_id=961,
        display_name="Mia",
        rng=random.Random(123),
    )

    assert result.outcome is not None
    assert result.blocked_by_readiness is False
    persisted = repository.get_player(user_id=960, guild_id=961)
    assert persisted is not None
    recent_activity = str(persisted["horse"]["recent_activity"])
    assert recent_activity.startswith(result.outcome.recent_activity_text)
    assert "Ride notes:" in recent_activity


def test_ride_horse_flow_horse_profile_shows_ride_recent_activity(tmp_path) -> None:
    """After /ride, /horse profile shows the ride's recent activity snippet."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=962, guild_id=963)
    repository.update_horse_state(
        user_id=962,
        guild_id=963,
        updates={"confidence": 50, "bond": 50, "skill": 50, "energy": 70, "health": 70},
    )

    ride_result = ride_horse_flow(
        repository=repository,
        user_id=962,
        guild_id=963,
        display_name="Mia",
        rng=random.Random(99),
    )

    profile_result = horse_profile_flow(
        repository=repository,
        user_id=962,
        guild_id=963,
        display_name="Mia",
    )

    assert ride_result.outcome is not None
    assert ride_result.blocked_by_readiness is False
    # The recent activity from the ride should appear in the horse profile.
    assert "Ride notes:" in profile_result.message


def test_ride_horse_flow_blocks_when_max_possible_losses_not_coverable(tmp_path) -> None:
    """Ride is refused unless energy>=30 and health>=10 (Option A safety gate)."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=968, guild_id=969)
    repository.update_horse_state(
        user_id=968,
        guild_id=969,
        updates={"confidence": 40, "bond": 40, "skill": 40, "energy": 29, "health": 9},
    )

    result = ride_horse_flow(
        repository=repository,
        user_id=968,
        guild_id=969,
        display_name="Mia",
        rng=random.Random(123),
    )

    assert result.has_adopted_horse is True
    assert result.blocked_by_readiness is True
    assert result.outcome is None
    assert result.ride_stat is None
    assert result.ride_stat_gain == 0
    assert result.energy_loss == 0
    assert result.health_loss == 0
    assert "tired and asks for an easy, caring day" in result.message
    assert "/feed" in result.message
    assert "/rest" in result.message

    persisted = repository.get_player(user_id=968, guild_id=969)
    assert persisted is not None
    assert persisted["horse"]["last_rode_at"] is None


def test_ride_horse_flow_uses_low_energy_and_health_mishap_narrative(tmp_path) -> None:
    """Low energy loss and triggered health loss should produce matching story cues."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=964, guild_id=965)
    repository.update_horse_state(
        user_id=964,
        guild_id=965,
        updates={"confidence": 50, "bond": 40, "skill": 10, "energy": 80, "health": 90},
    )

    # d100[0]=5 <= confidence -> no gain
    # d10[0..2]=1,1,1 -> energy_loss=3 (low)
    # d100[1]=95 > skill(10) -> health loss; d10[3]=2
    d100_iter = iter([5, 95])
    d10_iter = iter([1, 1, 1, 2])

    result = ride_horse_flow(
        repository=repository,
        user_id=964,
        guild_id=965,
        display_name="Mia",
        stat_selector=lambda: "confidence",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(11),
    )

    assert result.energy_loss == 3
    assert result.health_loss == 2
    assert "lightly winded" in result.message
    assert "small mishap" in result.message


def test_ride_horse_flow_uses_high_energy_and_steady_health_narrative(tmp_path) -> None:
    """High energy loss without health loss should use exhaustion and sure-footed cues."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=966, guild_id=967)
    repository.update_horse_state(
        user_id=966,
        guild_id=967,
        updates={"confidence": 30, "bond": 60, "skill": 95, "energy": 90, "health": 90},
    )

    # d100[0]=20 <= bond -> no gain
    # d10[0..2]=10,10,10 -> energy_loss=30 (high)
    # d100[1]=20 <= skill(95) -> no health loss
    d100_iter = iter([20, 20])
    d10_iter = iter([10, 10, 10])

    result = ride_horse_flow(
        repository=repository,
        user_id=966,
        guild_id=967,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(17),
    )

    assert result.energy_loss == 30
    assert result.health_loss == 0
    assert "deeply spent" in result.message
    assert "stays sure-footed" in result.message



