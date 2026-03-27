"""Shared flow utility helpers for service-layer state transitions."""

from __future__ import annotations

from datetime import UTC, datetime
import random
from typing import Callable

from .telemetry import TelemetryEventName, TelemetryLogger


def emit_telemetry(
    telemetry_logger: TelemetryLogger | None,
    event_name: TelemetryEventName,
    user_id: int,
    guild_id: int | None,
    candidate_id: str | None = None,
    horse_name: str | None = None,
    outcome_id: str | None = None,
    outcome_category: str | None = None,
) -> None:
    """Emit a telemetry event if a logger is configured."""
    if telemetry_logger is None:
        return
    telemetry_logger.emit(
        event_name=event_name,
        user_id=user_id,
        guild_id=guild_id,
        candidate_id=candidate_id,
        horse_name=horse_name,
        outcome_id=outcome_id,
        outcome_category=outcome_category,
    )


def roll_d10() -> int:
    """Return a uniform d10 roll for state deltas."""
    return random.randint(1, 10)


def roll_d100() -> int:
    """Return a uniform d100 roll for chance-based checks."""
    return random.randint(1, 100)


def chance_to_increase(
    current_value: int,
    d100_roll: Callable[[], int] | None,
    d10_roll: Callable[[], int] | None,
) -> int:
    """Roll 1d100 against current_value and return a clamped 1d10 gain on success."""
    check_roll = clamp_stat((d100_roll() if d100_roll is not None else roll_d100()), minimum=1)
    if check_roll <= current_value:
        return 0

    rolled_gain = d10_roll() if d10_roll is not None else roll_d10()
    return clamp_stat(rolled_gain, minimum=1, maximum=10)


def chance_to_decrease(
    checked_value: int,
    d100_roll: Callable[[], int] | None,
    d10_roll: Callable[[], int] | None,
) -> int:
    """Roll 1d100 against checked_value and return a clamped 1d10 loss on success."""
    check_roll = clamp_stat((d100_roll() if d100_roll is not None else roll_d100()), minimum=1)
    if check_roll <= checked_value:
        return 0

    rolled_loss = d10_roll() if d10_roll is not None else roll_d10()
    return clamp_stat(rolled_loss, minimum=1, maximum=10)


def slight_chance_to_decrease(
    checked_value: int,
    d100_roll: Callable[[], int] | None,
    d10_roll: Callable[[], int] | None,
) -> int:
    """Apply a stricter two-roll 1d100 check before returning a clamped 1d10 loss."""
    first_roll = clamp_stat((d100_roll() if d100_roll is not None else roll_d100()), minimum=1)
    second_roll = clamp_stat((d100_roll() if d100_roll is not None else roll_d100()), minimum=1)
    if first_roll <= checked_value or second_roll <= checked_value:
        return 0

    rolled_loss = d10_roll() if d10_roll is not None else roll_d10()
    return clamp_stat(rolled_loss, minimum=1, maximum=10)


def clamp_stat(value: int, minimum: int = 0, maximum: int = 100) -> int:
    """Clamp a horse state value within configured bounds."""
    return max(minimum, min(maximum, int(value)))


def timestamp_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(tz=UTC).isoformat()
