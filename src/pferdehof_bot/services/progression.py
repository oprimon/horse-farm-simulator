"""Progression flow services for training outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.repositories.player_repository import PlayerRecord

from .flow_utils import (
    chance_to_increase,
    clamp_stat,
    emit_telemetry,
    roll_d10,
    slight_chance_to_decrease,
    timestamp_now,
)
from .onboarding import PresentationField, ResponsePresentation
from .state_presentation import build_horse_state_presentation
from .telemetry import TelemetryLogger


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
