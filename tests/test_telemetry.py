"""Tests for telemetry emission and payload shape."""

from __future__ import annotations

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services import (
    choose_candidate_flow,
    feed_horse_flow,
    greet_horse_flow,
    groom_horse_flow,
    name_horse_flow,
    rest_horse_flow,
    ride_horse_flow,
    stable_roster_flow,
    start_onboarding_flow,
    train_horse_flow,
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
        horse_name: str | None = None,
        outcome_id: str | None = None,
        outcome_category: str | None = None,
    ) -> dict[str, object]:
        event = build_telemetry_event(
            event_name=event_name,
            user_id=user_id,
            guild_id=guild_id,
            timestamp=timestamp,
            candidate_id=candidate_id,
            horse_name=horse_name,
            outcome_id=outcome_id,
            outcome_category=outcome_category,
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


def test_build_telemetry_event_includes_mvp002_optional_dimensions() -> None:
    event = build_telemetry_event(
        event_name="ride_outcome",
        user_id=101,
        guild_id=202,
        timestamp="2026-03-25T08:30:00+00:00",
        horse_name="  Maple  ",
        outcome_id="steady_trot",
        outcome_category="good",
    )

    assert event == {
        "event_name": "ride_outcome",
        "user_id": 101,
        "guild_id": 202,
        "timestamp": "2026-03-25T08:30:00+00:00",
        "horse_name": "Maple",
        "outcome_id": "steady_trot",
        "outcome_category": "good",
    }


def _adopt_horse(repository: JsonPlayerRepository, user_id: int, guild_id: int, horse_name: str) -> None:
    start_onboarding_flow(
        repository=repository,
        user_id=user_id,
        guild_id=guild_id,
        display_name="Mia",
        candidate_seed=99,
    )
    choose_candidate_flow(
        repository=repository,
        user_id=user_id,
        guild_id=guild_id,
        display_name="Mia",
        candidate_id="A",
    )
    name_horse_flow(
        repository=repository,
        user_id=user_id,
        guild_id=guild_id,
        display_name="Mia",
        horse_name=horse_name,
    )


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


def test_mvp002_loop_flows_emit_required_events(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    telemetry_logger = InMemoryTelemetryLogger()

    _adopt_horse(repository=repository, user_id=901, guild_id=902, horse_name="Maple")

    feed_horse_flow(
        repository=repository,
        user_id=901,
        guild_id=902,
        display_name="Mia",
        d10_roll=lambda: 3,
        telemetry_logger=telemetry_logger,
    )
    groom_horse_flow(
        repository=repository,
        user_id=901,
        guild_id=902,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: 95,
        d10_roll=lambda: 2,
        telemetry_logger=telemetry_logger,
    )
    rest_horse_flow(
        repository=repository,
        user_id=901,
        guild_id=902,
        display_name="Mia",
        d10_roll=lambda: 4,
        telemetry_logger=telemetry_logger,
    )
    train_horse_flow(
        repository=repository,
        user_id=901,
        guild_id=902,
        display_name="Mia",
        d100_roll=lambda: 100,
        d10_roll=lambda: 1,
        telemetry_logger=telemetry_logger,
    )
    ride_horse_flow(
        repository=repository,
        user_id=901,
        guild_id=902,
        display_name="Mia",
        stat_selector=lambda: "confidence",
        d100_roll=lambda: 100,
        d10_roll=lambda: 1,
        telemetry_logger=telemetry_logger,
    )

    assert [event["event_name"] for event in telemetry_logger.events] == [
        "fed_horse",
        "groomed_horse",
        "rested_horse",
        "trained_horse",
        "rode_horse",
        "ride_outcome",
    ]
    assert all(event["user_id"] == 901 for event in telemetry_logger.events)
    assert all(event["guild_id"] == 902 for event in telemetry_logger.events)
    assert all("timestamp" in event for event in telemetry_logger.events)
    assert all(event.get("horse_name") == "Maple" for event in telemetry_logger.events)

    ride_outcome_event = telemetry_logger.events[-1]
    assert "outcome_id" in ride_outcome_event
    assert ride_outcome_event.get("outcome_category") in {"excellent", "good", "fair", "setback"}


def test_stable_view_emits_event_with_viewer_context(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    telemetry_logger = InMemoryTelemetryLogger()

    _adopt_horse(repository=repository, user_id=920, guild_id=921, horse_name="Maple")
    stable_roster_flow(
        repository=repository,
        guild_id=921,
        display_name="Mia",
        user_id=920,
        telemetry_logger=telemetry_logger,
    )

    assert telemetry_logger.events == [
        {
            "event_name": "viewed_stable",
            "user_id": 920,
            "guild_id": 921,
            "timestamp": telemetry_logger.events[0]["timestamp"],
        }
    ]


def test_mvp002_failure_paths_do_not_emit_new_events(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    telemetry_logger = InMemoryTelemetryLogger()

    feed_horse_flow(
        repository=repository,
        user_id=930,
        guild_id=931,
        display_name="Mia",
        telemetry_logger=telemetry_logger,
    )
    train_horse_flow(
        repository=repository,
        user_id=930,
        guild_id=931,
        display_name="Mia",
        telemetry_logger=telemetry_logger,
    )
    stable_roster_flow(
        repository=repository,
        guild_id=931,
        display_name="Mia",
        user_id=930,
        telemetry_logger=telemetry_logger,
    )

    assert telemetry_logger.events == []


def test_ride_blocked_by_readiness_does_not_emit_ride_events(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    telemetry_logger = InMemoryTelemetryLogger()

    _adopt_horse(repository=repository, user_id=940, guild_id=941, horse_name="Maple")
    repository.update_horse_state(
        user_id=940,
        guild_id=941,
        updates={"energy": 29, "health": 9},
    )

    ride_horse_flow(
        repository=repository,
        user_id=940,
        guild_id=941,
        display_name="Mia",
        telemetry_logger=telemetry_logger,
    )

    assert telemetry_logger.events == []