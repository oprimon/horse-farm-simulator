"""Progression flow services for training and ride outcomes."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Callable, Sequence

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.repositories.player_repository import PlayerRecord

from .flow_utils import (
    chance_to_decrease,
    chance_to_increase,
    clamp_stat,
    emit_telemetry,
    roll_d10,
    slight_chance_to_decrease,
    timestamp_now,
)
from .presentation_models import PresentationField, ResponsePresentation
from .ride_outcomes import RideOutcomeResult, select_ride_outcome
from .state_presentation import build_horse_state_presentation
from .telemetry import TelemetryLogger


_RIDE_GENERIC_OPENING_POOL: tuple[str, ...] = (
    "The path opens up gently, and the two of you settle into an easy rhythm.",
    "The ride begins with quiet focus, with hoofbeats and breath finding the same cadence.",
    "A calm stretch of trail gives you both space to settle and listen to each other.",
)

_RIDE_GENERIC_CLOSING_POOL: tuple[str, ...] = (
    "Back at the stable, the ride lingers as one of those moments that quietly matter.",
    "By the time you head home, both of you feel a little more in tune than before.",
    "When you turn for home, it feels like another small chapter in your shared story.",
)

_RIDE_ENERGY_NARRATIVE_BY_TIER: dict[str, tuple[str, ...]] = {
    "low": (
        "Even after the outing, {horse_name} is only lightly winded and still moving with ease.",
        "The effort leaves {horse_name} lightly winded, with plenty of spark still in the stride.",
    ),
    "medium": (
        "The work leaves {horse_name} noticeably tired, and the slower walk home feels well earned.",
        "By the end, {horse_name} is noticeably tired and grateful for the gentler pace back.",
    ),
    "high": (
        "That stretch pushes hard, and {horse_name} comes back deeply spent after giving so much.",
        "It is a demanding effort, and {horse_name} returns deeply spent but still willing.",
    ),
}

_RIDE_HEALTH_LOSS_NARRATIVE_BY_TIER: dict[str, tuple[str, ...]] = {
    "low": (
        "A small mishap on uneven ground causes a minor scrape before you steady things quickly.",
        "There is a small mishap over rough footing, leaving a minor scrape before you ease off.",
    ),
    "medium": (
        "A small mishap on the trail knocks the rhythm off for a moment and leaves clear soreness.",
        "One small mishap near a bend leads to a clumsy step and a bit more soreness than expected.",
    ),
    "high": (
        "A small mishap late in the ride turns into a heavier jolt, so you finish carefully and head home.",
        "Near the end, a small mishap causes a hard stumble, and you call the tougher work there.",
    ),
}

_RIDE_HEALTH_STEADY_POOL: tuple[str, ...] = (
    "Across the whole route, {horse_name} stays sure-footed and comfortable.",
    "No rough moment takes hold today; {horse_name} stays sure-footed from start to finish.",
)

_RIDE_STAT_GAIN_NARRATIVE_BY_TIER: dict[str, tuple[str, ...]] = {
    "low": (
        "You notice a little breakthrough in {stat_name} by the time you finish.",
        "By the end, there is a little breakthrough in {stat_name} worth building on.",
    ),
    "medium": (
        "The session lands as a solid breakthrough in {stat_name}.",
        "You can feel a solid breakthrough in {stat_name} settling in.",
    ),
    "high": (
        "Somewhere mid-ride, a major breakthrough in {stat_name} clicks into place.",
        "It turns into a major breakthrough in {stat_name} that you both seem to feel.",
    ),
}

_RIDE_STAT_NO_GAIN_POOL: tuple[str, ...] = (
    "There is no obvious jump in {stat_name} today, but the steady practice still counts.",
    "{stat_name_cap} stays about the same this time, yet the consistency will matter later.",
)


@dataclass(frozen=True)
class TrainHorseResult:
    """Result payload for `/train` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    blocked_by_readiness: bool
    skill_gain: int
    confidence_gain: int
    energy_cost: int
    health_loss: int
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class RideHorseResult:
    """Result payload for `/ride` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    blocked_by_readiness: bool
    outcome: RideOutcomeResult | None
    ride_stat: str | None
    ride_stat_gain: int
    energy_loss: int
    health_loss: int
    presentation: ResponsePresentation | None = None


def _build_presentation(
    *,
    title: str,
    description: str,
    accent: str | None = None,
    fields: tuple[PresentationField, ...] = (),
    footer: str | None = None,
) -> ResponsePresentation:
    """Build a normalized response presentation payload for command outputs."""
    return ResponsePresentation(
        title=title,
        description=description,
        fields=fields,
        accent=accent,
        footer=footer,
    )


def train_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    d100_roll: Callable[[], int] | None = None,
    d10_roll: Callable[[], int] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> TrainHorseResult:
    """Train an adopted horse with readable progression, risk, and energy tradeoffs."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to train yet. "
            "Start your adoption journey with `/start`."
        )
        return TrainHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            blocked_by_readiness=False,
            skill_gain=0,
            confidence_gain=0,
            energy_cost=0,
            health_loss=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    current_energy = clamp_stat(int(horse.get("energy") or 0))
    current_health = clamp_stat(int(horse.get("health") or 0))
    current_skill = clamp_stat(int(horse.get("skill") or 0))
    current_confidence = clamp_stat(int(horse.get("confidence") or 0))

    if current_energy < 10 or current_health < 10:
        state_presentation = build_horse_state_presentation(horse)
        recovery_guidance = "Try `/feed` or `/rest` first, then come back to `/train`."
        message = (
            f"You hold off on training {horse_name} for now. "
            f"{horse_name} feels {state_presentation.readiness_feel}. "
            f"Recovery Tip: {recovery_guidance}"
        )
        return TrainHorseResult(
            player=player,
            message=message,
            has_adopted_horse=True,
            blocked_by_readiness=True,
            skill_gain=0,
            confidence_gain=0,
            energy_cost=0,
            health_loss=0,
            presentation=_build_presentation(
                title="Training Deferred",
                description=(
                    f"You hold off on training {horse_name} for now. "
                    f"{horse_name} feels {state_presentation.readiness_feel}."
                ),
                accent="warning",
                fields=(
                    PresentationField(name="Recovery Tip", value=recovery_guidance),
                ),
            ),
        )

    skill_gain = chance_to_increase(
        current_value=current_skill,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )
    confidence_gain = chance_to_increase(
        current_value=current_confidence,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )
    energy_cost_roll = d10_roll() if d10_roll is not None else roll_d10()
    energy_cost = clamp_stat(energy_cost_roll, minimum=1, maximum=10)
    health_loss = slight_chance_to_decrease(
        checked_value=current_skill,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )

    updated_skill = clamp_stat(current_skill + skill_gain)
    updated_confidence = clamp_stat(current_confidence + confidence_gain)
    updated_energy = clamp_stat(current_energy - energy_cost)
    updated_health = clamp_stat(current_health - health_loss)

    recent_activity_parts = [f"You trained {horse_name}"]
    if skill_gain > 0:
        recent_activity_parts.append(f"{horse_name} picked up the lesson well (+{skill_gain} skill)")
    else:
        recent_activity_parts.append(f"{horse_name} stayed patient through a gentle practice")

    if confidence_gain > 0:
        recent_activity_parts.append(f"and warmed to the work (+{confidence_gain} confidence)")

    recent_activity_parts.append(f"while using up some energy (-{energy_cost} energy)")

    if health_loss > 0:
        recent_activity_parts.append(f"and came away a little sore (-{health_loss} health)")

    recent_activity = ". ".join(recent_activity_parts) + "."

    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates={
            "skill": updated_skill,
            "confidence": updated_confidence,
            "energy": updated_energy,
            "health": updated_health,
            "last_trained_at": timestamp_now(),
            "recent_activity": recent_activity,
        },
    )
    emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="trained_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )

    updated_horse = updated_player.get("horse") or {}
    state_presentation = build_horse_state_presentation(updated_horse)
    result_parts = []
    if skill_gain > 0:
        result_parts.append(f"+{skill_gain} skill")
    if confidence_gain > 0:
        result_parts.append(f"+{confidence_gain} confidence")
    result_parts.append(f"-{energy_cost} energy")
    if health_loss > 0:
        result_parts.append(f"-{health_loss} health")
    result_summary = ", ".join(result_parts)

    message = (
        f"You guide {horse_name} through a focused training session. "
        f"{horse_name} comes away {state_presentation.skill_feel} and {state_presentation.confidence_feel} ({result_summary}). "
        f"If {horse_name} still feels ready later, `/ride` is the next natural step."
    )
    return TrainHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        blocked_by_readiness=False,
        skill_gain=skill_gain,
        confidence_gain=confidence_gain,
        energy_cost=energy_cost,
        health_loss=health_loss,
        presentation=_build_presentation(
            title=f"Training Session With {horse_name}",
            description=(
                f"{horse_name} now feels {state_presentation.skill_feel} and "
                f"{state_presentation.confidence_feel}."
            ),
            accent="success",
            fields=(
                PresentationField(name="Skill", value=f"+{skill_gain}" if skill_gain > 0 else "No increase", inline=True),
                PresentationField(
                    name="Confidence",
                    value=f"+{confidence_gain}" if confidence_gain > 0 else "No increase",
                    inline=True,
                ),
                PresentationField(name="Energy", value=f"-{energy_cost}", inline=True),
                PresentationField(name="Health", value=f"-{health_loss}" if health_loss > 0 else "No loss", inline=True),
                PresentationField(name="Next Step", value=f"If {horse_name} feels ready, try `/ride`."),
            ),
        ),
    )


def ride_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    stat_selector: Callable[[], str] | None = None,
    d100_roll: Callable[[], int] | None = None,
    d10_roll: Callable[[], int] | None = None,
    rng: random.Random | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> RideHorseResult:
    """Take an adopted horse on a ride and persist the outcome as recent activity."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to ride yet. "
            "Start your adoption journey with `/start`."
        )
        return RideHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            blocked_by_readiness=False,
            outcome=None,
            ride_stat=None,
            ride_stat_gain=0,
            energy_loss=0,
            health_loss=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    current_energy = clamp_stat(int(horse.get("energy") or 0))
    current_health = clamp_stat(int(horse.get("health") or 0))
    current_skill = clamp_stat(int(horse.get("skill") or 0))
    current_confidence = clamp_stat(int(horse.get("confidence") or 0))
    current_bond = clamp_stat(int(horse.get("bond") or 0))

    if current_energy < 30 or current_health < 10:
        state_presentation = build_horse_state_presentation(horse)
        recovery_guidance = "Try `/feed` or `/rest` first, then come back to `/ride`."
        message = (
            f"You decide not to ride {horse_name} right now. "
            f"{horse_name} feels {state_presentation.readiness_feel}. "
            f"Recovery Tip: {recovery_guidance}"
        )
        return RideHorseResult(
            player=player,
            message=message,
            has_adopted_horse=True,
            blocked_by_readiness=True,
            outcome=None,
            ride_stat=None,
            ride_stat_gain=0,
            energy_loss=0,
            health_loss=0,
            presentation=_build_presentation(
                title="Ride Deferred",
                description=(
                    f"You decide not to ride {horse_name} right now. "
                    f"{horse_name} feels {state_presentation.readiness_feel}."
                ),
                accent="warning",
                fields=(
                    PresentationField(name="Recovery Tip", value=recovery_guidance),
                ),
            ),
        )

    selected_stat = stat_selector() if stat_selector is not None else random.choice(("confidence", "bond"))
    if selected_stat not in {"confidence", "bond"}:
        selected_stat = "confidence"
    current_selected_value = current_confidence if selected_stat == "confidence" else current_bond

    outcome = select_ride_outcome(
        horse_name=horse_name,
        energy=current_energy,
        confidence=current_confidence,
        bond=current_bond,
        skill=current_skill,
        rng=rng,
    )

    ride_stat_gain = chance_to_increase(
        current_value=current_selected_value,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )

    roll_1 = d10_roll() if d10_roll is not None else roll_d10()
    roll_2 = d10_roll() if d10_roll is not None else roll_d10()
    roll_3 = d10_roll() if d10_roll is not None else roll_d10()
    energy_loss = clamp_stat(roll_1 + roll_2 + roll_3, minimum=3, maximum=30)

    health_loss = chance_to_decrease(
        checked_value=current_skill,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )

    updated_selected = clamp_stat(current_selected_value + ride_stat_gain)
    updated_energy = clamp_stat(current_energy - energy_loss)
    updated_health = clamp_stat(current_health - health_loss)

    _rng = rng if rng is not None else random.Random()
    contextual_story, contextual_recent = _compose_ride_roll_narrative(
        horse_name=horse_name,
        ride_stat=selected_stat,
        ride_stat_gain=ride_stat_gain,
        energy_loss=energy_loss,
        health_loss=health_loss,
        rng=_rng,
    )

    recent_activity = f"{outcome.recent_activity_text} {contextual_recent}"
    updates: dict[str, object] = {
        selected_stat: updated_selected,
        "energy": updated_energy,
        "health": updated_health,
        "last_rode_at": timestamp_now(),
        "recent_activity": recent_activity,
    }
    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates=updates,
    )
    emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="rode_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )
    emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="ride_outcome",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
        outcome_id=outcome.outcome_id,
        outcome_category=outcome.category,
    )

    result_parts: list[str] = []
    if ride_stat_gain > 0:
        result_parts.append(f"+{ride_stat_gain} {selected_stat}")
    result_parts.append(f"-{energy_loss} energy")
    if health_loss > 0:
        result_parts.append(f"-{health_loss} health")
    result_summary = ", ".join(result_parts)

    message = (
        f"{outcome.story_text}\n\n"
        f"{contextual_story}\n\n"
        f"({result_summary})\n\nUse `/horse profile` to see {horse_name}'s updated profile."
    )
    return RideHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        blocked_by_readiness=False,
        outcome=outcome,
        ride_stat=selected_stat,
        ride_stat_gain=ride_stat_gain,
        energy_loss=energy_loss,
        health_loss=health_loss,
        presentation=_build_presentation(
            title="Ride Complete",
            description=outcome.story_text,
            accent=outcome.accent,
            fields=(
                PresentationField(name="Ride Notes", value=contextual_story),
                PresentationField(
                    name="Result",
                    value=(
                        f"{selected_stat.capitalize()}: +{ride_stat_gain}\n"
                        f"Energy: -{energy_loss}\n"
                        + (f"Health: -{health_loss}" if health_loss > 0 else "Health: no loss")
                    ),
                    inline=True,
                ),
                PresentationField(name="Next Step", value=f"Use `/horse profile` to check {horse_name}'s updated state."),
            ),
            footer=f"Outcome: {outcome.category}",
        ),
    )


def _compose_ride_roll_narrative(
    horse_name: str,
    ride_stat: str,
    ride_stat_gain: int,
    energy_loss: int,
    health_loss: int,
    rng: random.Random,
) -> tuple[str, str]:
    """Build descriptive ride text from roll outcomes with future-stat compatibility."""
    stat_name = ride_stat.replace("_", " ").strip() or "readiness"
    stat_name_cap = stat_name.capitalize()

    energy_tier = _delta_tier(amount=energy_loss, max_amount=30)
    health_tier = _delta_tier(amount=health_loss, max_amount=10)
    gain_tier = _delta_tier(amount=ride_stat_gain, max_amount=10)

    parts: list[str] = [_pick(pool=_RIDE_GENERIC_OPENING_POOL, rng=rng)]
    parts.append(
        _pick(pool=_RIDE_ENERGY_NARRATIVE_BY_TIER[energy_tier], rng=rng).format(horse_name=horse_name)
    )

    if health_loss > 0:
        parts.append(
            _pick(pool=_RIDE_HEALTH_LOSS_NARRATIVE_BY_TIER[health_tier], rng=rng).format(
                horse_name=horse_name
            )
        )
    else:
        parts.append(_pick(pool=_RIDE_HEALTH_STEADY_POOL, rng=rng).format(horse_name=horse_name))

    if ride_stat_gain > 0:
        parts.append(
            _pick(pool=_RIDE_STAT_GAIN_NARRATIVE_BY_TIER[gain_tier], rng=rng).format(
                stat_name=stat_name,
                stat_name_cap=stat_name_cap,
            )
        )
    else:
        parts.append(
            _pick(pool=_RIDE_STAT_NO_GAIN_POOL, rng=rng).format(
                stat_name=stat_name,
                stat_name_cap=stat_name_cap,
            )
        )

    parts.append(_pick(pool=_RIDE_GENERIC_CLOSING_POOL, rng=rng))

    story_text = " ".join(parts)
    recent_text = (
        f"Ride notes: {_build_recent_energy_fragment(horse_name=horse_name, energy_tier=energy_tier)} "
        f"{_build_recent_health_fragment(health_loss=health_loss)} "
        f"{_build_recent_stat_fragment(stat_name=stat_name, ride_stat_gain=ride_stat_gain)}"
    )
    return story_text, recent_text


def _build_recent_energy_fragment(horse_name: str, energy_tier: str) -> str:
    if energy_tier == "low":
        return f"{horse_name} is lightly winded."
    if energy_tier == "medium":
        return f"{horse_name} is noticeably tired."
    return f"{horse_name} is deeply spent."


def _build_recent_health_fragment(health_loss: int) -> str:
    if health_loss > 0:
        return "A small mishap left some soreness."
    return "No rough moment caused health trouble."


def _build_recent_stat_fragment(stat_name: str, ride_stat_gain: int) -> str:
    if ride_stat_gain > 0:
        return f"{stat_name.capitalize()} saw a breakthrough (+{ride_stat_gain})."
    return f"{stat_name.capitalize()} held steady this ride."


def _delta_tier(amount: int, max_amount: int) -> str:
    """Map a positive delta amount to low/medium/high narrative tiers."""
    normalized = max(0, min(max_amount, int(amount)))
    if normalized <= 0:
        return "low"
    if normalized <= max_amount // 3:
        return "low"
    if normalized <= (2 * max_amount) // 3:
        return "medium"
    return "high"


def _pick(pool: Sequence[str], rng: random.Random) -> str:
    return rng.choice(tuple(pool))
