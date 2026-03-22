"""Structured telemetry helpers for onboarding funnel events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Literal, Protocol, TypedDict


TelemetryEventName = Literal[
    "start_onboarding",
    "viewed_candidates",
    "chose_candidate",
    "named_horse",
    "first_interaction",
]


class TelemetryEvent(TypedDict, total=False):
    """Serialized telemetry event payload."""

    event_name: TelemetryEventName
    user_id: int
    guild_id: int | None
    timestamp: str
    candidate_id: str


class TelemetryLogger(Protocol):
    """Contract for structured telemetry sinks."""

    def emit(
        self,
        event_name: TelemetryEventName,
        user_id: int,
        guild_id: int | None,
        *,
        timestamp: str | None = None,
        candidate_id: str | None = None,
    ) -> TelemetryEvent:
        """Persist and return a telemetry payload."""


def build_telemetry_event(
    event_name: TelemetryEventName,
    user_id: int,
    guild_id: int | None,
    *,
    timestamp: str | None = None,
    candidate_id: str | None = None,
) -> TelemetryEvent:
    """Create a normalized telemetry payload."""
    event: TelemetryEvent = {
        "event_name": event_name,
        "user_id": int(user_id),
        "guild_id": int(guild_id) if guild_id is not None else None,
        "timestamp": timestamp or datetime.now(UTC).isoformat(),
    }
    if candidate_id is not None:
        event["candidate_id"] = str(candidate_id).upper()
    return event


@dataclass(slots=True)
class FileTelemetryLogger:
    """Append telemetry events to a JSON Lines file."""

    storage_path: str | Path

    def emit(
        self,
        event_name: TelemetryEventName,
        user_id: int,
        guild_id: int | None,
        *,
        timestamp: str | None = None,
        candidate_id: str | None = None,
    ) -> TelemetryEvent:
        event = build_telemetry_event(
            event_name=event_name,
            user_id=user_id,
            guild_id=guild_id,
            timestamp=timestamp,
            candidate_id=candidate_id,
        )
        storage_path = Path(self.storage_path)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        with storage_path.open("a", encoding="utf-8") as telemetry_file:
            telemetry_file.write(json.dumps(event) + "\n")
        return event
