"""Tests for telemetry emission and payload shape."""

from __future__ import annotations

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services import (
    choose_candidate_flow,
    greet_horse_flow,
    name_horse_flow,
    start_onboarding_flow,
    view_candidates_flow,
    build_telemetry_event,
)


class InMemoryTelemetryLogger:
    """Simple telemetry sink for unit tests."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def emit(
        self,
        event_name: str,
        user_id: int,
        guild_id: int | None,
        *,
        timestamp: str | None = None,
        candidate_id: str | None = None,
    ) -> dict[str, object]:
        event = build_telemetry_event(
            event_name=event_name,
            user_id=user_id,
            guild_id=guild_id,
            timestamp=timestamp,
            candidate_id=candidate_id,
        )
        self.events.append(event)
        return event


def test_build_telemetry_event_includes_required_payload_keys() -> None:
    event = build_telemetry_event(
        event_name="chose_candidate",
        user_id=101,
        guild_id=202,
        timestamp="2026-03-22T18:30:00+00:00",
        candidate_id="b",
    )

    assert event == {
        "event_name": "chose_candidate",
        "user_id": 101,
        "guild_id": 202,
        "timestamp": "2026-03-22T18:30:00+00:00",
        "candidate_id": "B",
    }


def test_onboarding_funnel_emits_required_events(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    telemetry_logger = InMemoryTelemetryLogger()

    start_onboarding_flow(
        repository=repository,
        user_id=701,
        guild_id=702,
        display_name="Mia",
        candidate_seed=123,
        telemetry_logger=telemetry_logger,
    )
    view_candidates_flow(
        repository=repository,
        user_id=701,
        guild_id=702,
        display_name="Mia",
        telemetry_logger=telemetry_logger,
    )
    choose_candidate_flow(
        repository=repository,
        user_id=701,
        guild_id=702,
        display_name="Mia",
        candidate_id="A",
        telemetry_logger=telemetry_logger,
    )
    name_horse_flow(
        repository=repository,
        user_id=701,
        guild_id=702,
        display_name="Mia",
        horse_name="Luna",
        telemetry_logger=telemetry_logger,
    )
    greet_horse_flow(
        repository=repository,
        user_id=701,
        guild_id=702,
        display_name="Mia",
        telemetry_logger=telemetry_logger,
    )
    greet_horse_flow(
        repository=repository,
        user_id=701,
        guild_id=702,
        display_name="Mia",
        telemetry_logger=telemetry_logger,
    )

    assert [event["event_name"] for event in telemetry_logger.events] == [
        "start_onboarding",
        "viewed_candidates",
        "chose_candidate",
        "named_horse",
        "first_interaction",
    ]
    assert telemetry_logger.events[2]["candidate_id"] == "A"
    assert telemetry_logger.events[3]["candidate_id"] == "A"


def test_failed_branches_do_not_emit_telemetry(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    telemetry_logger = InMemoryTelemetryLogger()

    view_candidates_flow(
        repository=repository,
        user_id=801,
        guild_id=802,
        display_name="Mia",
        telemetry_logger=telemetry_logger,
    )
    choose_candidate_flow(
        repository=repository,
        user_id=801,
        guild_id=802,
        display_name="Mia",
        candidate_id="Z",
        telemetry_logger=telemetry_logger,
    )
    greet_horse_flow(
        repository=repository,
        user_id=801,
        guild_id=802,
        display_name="Mia",
        telemetry_logger=telemetry_logger,
    )

    assert telemetry_logger.events == []