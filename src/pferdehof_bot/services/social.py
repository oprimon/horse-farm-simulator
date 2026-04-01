"""Social interaction flow service for horse-to-horse cooperative actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import random
from pathlib import Path
from typing import Callable

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.repositories.player_repository import PlayerRecord

from .flow_utils import clamp_stat, emit_telemetry, roll_d10, timestamp_now
from .playdate_story_engine import PlaydateStoryContext, render_playdate_narrative
from .presentation_models import PresentationField, ResponsePresentation
from .telemetry import TelemetryLogger


SOCIALIZE_COOLDOWN_SECONDS = 60 * 60
STORY_PACKS_DIR = Path("stories")


@dataclass(frozen=True)
class SocializeHorseResult:
    """Result payload for `/playdate` command execution."""

    initiator_player: PlayerRecord | None
    target_player: PlayerRecord | None
    message: str
    success: bool
    blocked_by_cooldown: bool
    has_initiator_horse: bool
    has_target_horse: bool
    initiator_bond_gain: int
    initiator_confidence_gain: int
    target_bond_gain: int
    target_confidence_gain: int
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


def socialize_horses_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    target_user_id: int,
    guild_id: int | None,
    display_name: str,
    target_display_name: str,
    d10_roll: Callable[[], int] | None = None,
    now_provider: Callable[[], str] | None = None,
    rng: random.Random | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> SocializeHorseResult:
    """Run a cooperative horse interaction between two players in the same guild."""
    if guild_id is None:
        message = "Horse playdates work only inside a server stable. Use this command in a guild channel."
        return SocializeHorseResult(
            initiator_player=None,
            target_player=None,
            message=message,
            success=False,
            blocked_by_cooldown=False,
            has_initiator_horse=False,
            has_target_horse=False,
            initiator_bond_gain=0,
            initiator_confidence_gain=0,
            target_bond_gain=0,
            target_confidence_gain=0,
            presentation=_build_presentation(
                title="Playdate Unavailable",
                description=message,
                accent="warning",
            ),
        )

    if user_id == target_user_id:
        message = "Choose another rider for a playdate. Your horse cannot playdate with itself."
        return SocializeHorseResult(
            initiator_player=repository.get_player(user_id=user_id, guild_id=guild_id),
            target_player=None,
            message=message,
            success=False,
            blocked_by_cooldown=False,
            has_initiator_horse=False,
            has_target_horse=False,
            initiator_bond_gain=0,
            initiator_confidence_gain=0,
            target_bond_gain=0,
            target_confidence_gain=0,
            presentation=_build_presentation(
                title="Pick A Different Rider",
                description=message,
                accent="warning",
            ),
        )

    initiator_player = repository.get_player(user_id=user_id, guild_id=guild_id)
    target_player = repository.get_player(user_id=target_user_id, guild_id=guild_id)

    if initiator_player is None or not bool(initiator_player.get("adopted", False)):
        message = "You need an adopted horse first. Start with `/start` before scheduling a playdate."
        return SocializeHorseResult(
            initiator_player=initiator_player,
            target_player=target_player,
            message=message,
            success=False,
            blocked_by_cooldown=False,
            has_initiator_horse=False,
            has_target_horse=bool(target_player and target_player.get("adopted", False)),
            initiator_bond_gain=0,
            initiator_confidence_gain=0,
            target_bond_gain=0,
            target_confidence_gain=0,
            presentation=_build_presentation(
                title="No Horse Ready",
                description=message,
                accent="warning",
            ),
        )

    if target_player is None or not bool(target_player.get("adopted", False)):
        message = f"{target_display_name} has no adopted horse yet. Ask them to run `/start` first."
        return SocializeHorseResult(
            initiator_player=initiator_player,
            target_player=target_player,
            message=message,
            success=False,
            blocked_by_cooldown=False,
            has_initiator_horse=True,
            has_target_horse=False,
            initiator_bond_gain=0,
            initiator_confidence_gain=0,
            target_bond_gain=0,
            target_confidence_gain=0,
            presentation=_build_presentation(
                title="Target Horse Missing",
                description=message,
                accent="warning",
            ),
        )

    initiated_horse = initiator_player.get("horse") or {}
    target_horse = target_player.get("horse") or {}
    initiator_horse_name = str(initiated_horse.get("name") or "Your horse")
    target_horse_name = str(target_horse.get("name") or "Their horse")

    now_timestamp = now_provider() if now_provider is not None else timestamp_now()
    remaining_seconds = _cooldown_remaining_seconds(
        last_socialized_at=initiated_horse.get("last_socialized_at"),
        now_timestamp=now_timestamp,
    )
    if remaining_seconds > 0:
        minutes = (remaining_seconds + 59) // 60
        message = (
            f"{initiator_horse_name} needs a little break before another playdate. "
            f"Try again in about {minutes} minute(s)."
        )
        return SocializeHorseResult(
            initiator_player=initiator_player,
            target_player=target_player,
            message=message,
            success=False,
            blocked_by_cooldown=True,
            has_initiator_horse=True,
            has_target_horse=True,
            initiator_bond_gain=0,
            initiator_confidence_gain=0,
            target_bond_gain=0,
            target_confidence_gain=0,
            presentation=_build_presentation(
                title="Playdate Cooldown",
                description=message,
                accent="info",
            ),
        )

    initiator_bond_gain = _roll_small_gain(d10_roll)
    initiator_confidence_gain = _roll_small_gain(d10_roll)
    target_bond_gain = _roll_small_gain(d10_roll)
    target_confidence_gain = _roll_small_gain(d10_roll)

    story_context = PlaydateStoryContext(
        initiator_horse_name=initiator_horse_name,
        target_horse_name=target_horse_name,
        initiator_player_name=display_name,
        target_player_name=target_display_name,
        initiator_energy=int(initiated_horse.get("energy") or 0),
        target_energy=int(target_horse.get("energy") or 0),
        initiator_confidence=int(initiated_horse.get("confidence") or 0),
        target_confidence=int(target_horse.get("confidence") or 0),
        initiator_bond=int(initiated_horse.get("bond") or 0),
        target_bond=int(target_horse.get("bond") or 0),
        initiator_health=int(initiated_horse.get("health") or 0),
        target_health=int(target_horse.get("health") or 0),
    )
    try:
        narrative = render_playdate_narrative(story_context, rng=rng, story_packs_dir=STORY_PACKS_DIR)
    except Exception:
        # Fallback: use built-in defaults if a community story pack causes a render error.
        narrative = render_playdate_narrative(story_context, rng=rng, story_packs_dir=None)

    initiator_updates = {
        "bond": clamp_stat(int(initiated_horse.get("bond") or 0) + initiator_bond_gain),
        "confidence": clamp_stat(int(initiated_horse.get("confidence") or 0) + initiator_confidence_gain),
        "last_socialized_at": now_timestamp,
        "recent_activity": (
            f"{initiator_horse_name} shared a playful stable moment with {target_horse_name} "
            f"(+{initiator_bond_gain} bond, +{initiator_confidence_gain} confidence)."
        ),
    }
    target_updates = {
        "bond": clamp_stat(int(target_horse.get("bond") or 0) + target_bond_gain),
        "confidence": clamp_stat(int(target_horse.get("confidence") or 0) + target_confidence_gain),
        "recent_activity": (
            f"{target_horse_name} played with {initiator_horse_name} from {display_name}'s stable routine "
            f"(+{target_bond_gain} bond, +{target_confidence_gain} confidence)."
        ),
    }

    updated_initiator, updated_target = repository.update_two_horse_states(
        user_id=user_id,
        target_user_id=target_user_id,
        guild_id=guild_id,
        updates=initiator_updates,
        target_updates=target_updates,
    )

    emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="social_interaction_completed",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=initiator_horse_name,
        outcome_id=narrative.story_id,
        outcome_category=narrative.tone,
    )

    message = (
        f"{display_name} sets up a playdate with {target_display_name}. {narrative.message}"
    )
    return SocializeHorseResult(
        initiator_player=updated_initiator,
        target_player=updated_target,
        message=message,
        success=True,
        blocked_by_cooldown=False,
        has_initiator_horse=True,
        has_target_horse=True,
        initiator_bond_gain=initiator_bond_gain,
        initiator_confidence_gain=initiator_confidence_gain,
        target_bond_gain=target_bond_gain,
        target_confidence_gain=target_confidence_gain,
        presentation=_build_presentation(
            title=f"Stable Playdate - {narrative.title}",
            description=message,
            accent="success",
            fields=(
                PresentationField(
                    name=initiator_horse_name,
                    value=(
                        f"+{initiator_bond_gain} bond, +{initiator_confidence_gain} confidence"
                    ),
                    inline=True,
                ),
                PresentationField(
                    name=target_horse_name,
                    value=(
                        f"+{target_bond_gain} bond, +{target_confidence_gain} confidence"
                    ),
                    inline=True,
                ),
            ),
            footer="Playdates are on cooldown for you for 60 minutes.",
        ),
    )


def _roll_small_gain(d10_roll: Callable[[], int] | None) -> int:
    roll = d10_roll() if d10_roll is not None else roll_d10()
    clamped = clamp_stat(roll, minimum=1, maximum=10)
    if clamped <= 4:
        return 1
    if clamped <= 8:
        return 2
    return 3


def _cooldown_remaining_seconds(last_socialized_at: object, now_timestamp: str) -> int:
    previous = _parse_iso_timestamp(last_socialized_at)
    current = _parse_iso_timestamp(now_timestamp)
    if previous is None or current is None:
        return 0

    cooldown_end = previous + timedelta(seconds=SOCIALIZE_COOLDOWN_SECONDS)
    if current >= cooldown_end:
        return 0
    return int((cooldown_end - current).total_seconds())


def _parse_iso_timestamp(raw_timestamp: object) -> datetime | None:
    if raw_timestamp is None:
        return None
    text = str(raw_timestamp).strip()
    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)