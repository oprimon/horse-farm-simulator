"""Care-loop flow services for feed, groom, and rest actions."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Callable

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.repositories.player_repository import PlayerRecord

from .flow_utils import clamp_stat, emit_telemetry, roll_d10, roll_d100, timestamp_now
from .onboarding import PresentationField, ResponsePresentation
from .telemetry import TelemetryLogger


@dataclass(frozen=True)
class FeedHorseResult:
    """Result payload for `/feed` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    energy_gain: int
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class GroomHorseResult:
    """Result payload for `/groom` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    groomed_stat: str | None
    stat_gain: int
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class RestHorseResult:
    """Result payload for `/rest` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    health_gain: int
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


def feed_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    d10_roll: Callable[[], int] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> FeedHorseResult:
    """Feed an adopted horse to restore energy and persist recent activity."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to feed yet. "
            "Start your adoption journey with `/start`."
        )
        return FeedHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            energy_gain=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    current_energy = int(horse.get("energy") or 0)
    roll = d10_roll() if d10_roll is not None else roll_d10()
    energy_gain = clamp_stat(roll, minimum=1, maximum=10)
    updated_energy = clamp_stat(current_energy + energy_gain)
    recent_activity = (
        f"You fed {horse_name}, and {horse_name} perked up right away (+{energy_gain} energy)."
    )

    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates={
            "energy": updated_energy,
            "last_fed_at": timestamp_now(),
            "recent_activity": recent_activity,
        },
    )
    emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="fed_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )

    message = (
        f"You offer a warm feed to {horse_name}. "
        f"{horse_name} munches happily and feels brighter (+{energy_gain} energy)."
    )
    return FeedHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        energy_gain=energy_gain,
        presentation=_build_presentation(
            title=f"{horse_name} Enjoyed The Feed",
            description=message,
            accent="success",
            fields=(
                PresentationField(name="Energy Gained", value=f"+{energy_gain}"),
            ),
        ),
    )


def groom_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    stat_selector: Callable[[], str] | None = None,
    d100_roll: Callable[[], int] | None = None,
    d10_roll: Callable[[], int] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> GroomHorseResult:
    """Groom an adopted horse with a chance to increase bond or health."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to groom yet. "
            "Start your adoption journey with `/start`."
        )
        return GroomHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            groomed_stat=None,
            stat_gain=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    selected_stat = stat_selector() if stat_selector is not None else random.choice(("bond", "health"))
    if selected_stat not in {"bond", "health"}:
        selected_stat = "bond"

    current_value = clamp_stat(int(horse.get(selected_stat) or 0))
    check_roll = clamp_stat((d100_roll() if d100_roll is not None else roll_d100()), minimum=1)

    stat_gain = 0
    if check_roll > current_value:
        rolled_gain = d10_roll() if d10_roll is not None else roll_d10()
        stat_gain = clamp_stat(rolled_gain, minimum=1, maximum=10)

    updated_value = clamp_stat(current_value + stat_gain)
    stat_label = "bond" if selected_stat == "bond" else "health"

    if stat_gain > 0:
        reaction_text = (
            f"{horse_name} melts into the brushing and seems noticeably calmer (+{stat_gain} {stat_label})."
        )
    else:
        reaction_text = (
            f"{horse_name} relaxes into the grooming routine. It is a quiet, comforting moment today."
        )

    recent_activity = f"You groomed {horse_name}. {reaction_text}"
    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates={
            selected_stat: updated_value,
            "last_groomed_at": timestamp_now(),
            "recent_activity": recent_activity,
        },
    )
    emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="groomed_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )

    message = f"You groom {horse_name} carefully. {reaction_text}"
    return GroomHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        groomed_stat=selected_stat,
        stat_gain=stat_gain,
        presentation=_build_presentation(
            title=f"{horse_name} Is Groomed",
            description=message,
            accent="success",
            fields=(
                PresentationField(name="Stat Focus", value=stat_label.capitalize(), inline=True),
                PresentationField(name="Gain", value=f"+{stat_gain}" if stat_gain > 0 else "No increase", inline=True),
            ),
        ),
    )


def rest_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    d10_roll: Callable[[], int] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> RestHorseResult:
    """Rest an adopted horse to restore health and persist recent activity."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to rest yet. "
            "Start your adoption journey with `/start`."
        )
        return RestHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            health_gain=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    current_health = int(horse.get("health") or 0)
    roll = d10_roll() if d10_roll is not None else roll_d10()
    health_gain = clamp_stat(roll, minimum=1, maximum=10)
    updated_health = clamp_stat(current_health + health_gain)
    recent_activity = (
        f"{horse_name} rested quietly in the stable and feels healthier (+{health_gain} health)."
    )

    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates={
            "health": updated_health,
            "last_rested_at": timestamp_now(),
            "recent_activity": recent_activity,
        },
    )
    emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="rested_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )

    message = (
        f"You settle {horse_name} in for a comfortable rest. "
        f"{horse_name} dozes peacefully and wakes up feeling better (+{health_gain} health)."
    )
    return RestHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        health_gain=health_gain,
        presentation=_build_presentation(
            title=f"{horse_name} Had A Rest",
            description=message,
            accent="success",
            fields=(
                PresentationField(name="Health Gained", value=f"+{health_gain}"),
            ),
        ),
    )
