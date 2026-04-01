"""Tests for horse-to-horse social interaction flow."""

from __future__ import annotations

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services.lifecycle import choose_candidate_flow, name_horse_flow, start_onboarding_flow
from pferdehof_bot.services.social import socialize_horses_flow
from pferdehof_bot.services.telemetry import TelemetryEvent, TelemetryEventName, build_telemetry_event


class InMemoryTelemetryLogger:
    """Simple telemetry sink for social flow tests."""

    def __init__(self) -> None:
        self.events: list[TelemetryEvent] = []

    def emit(
        self,
        event_name: TelemetryEventName,
        user_id: int,
        guild_id: int | None,
        *,
        timestamp: str | None = None,
        candidate_id: str | None = None,
        horse_name: str | None = None,
        outcome_id: str | None = None,
        outcome_category: str | None = None,
    ) -> TelemetryEvent:
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


def _adopt_horse(repository: JsonPlayerRepository, user_id: int, guild_id: int, horse_name: str) -> None:
    start_onboarding_flow(
        repository=repository,
        user_id=user_id,
        guild_id=guild_id,
        display_name="Mia",
        candidate_seed=99 + user_id,
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


def test_socialize_horses_flow_updates_both_horses_and_emits_event(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    telemetry_logger = InMemoryTelemetryLogger()
    _adopt_horse(repository=repository, user_id=101, guild_id=202, horse_name="Nova")
    _adopt_horse(repository=repository, user_id=102, guild_id=202, horse_name="Luna")

    result = socialize_horses_flow(
        repository=repository,
        user_id=101,
        target_user_id=102,
        guild_id=202,
        display_name="Mia",
        target_display_name="Rowan",
        d10_roll=lambda: 10,
        now_provider=lambda: "2026-04-01T10:00:00+00:00",
        telemetry_logger=telemetry_logger,
    )

    assert result.success is True
    assert result.blocked_by_cooldown is False
    assert result.initiator_bond_gain == 3
    assert result.initiator_confidence_gain == 3
    assert result.target_bond_gain == 3
    assert result.target_confidence_gain == 3

    initiator = repository.get_player(user_id=101, guild_id=202)
    target = repository.get_player(user_id=102, guild_id=202)
    assert initiator is not None
    assert target is not None
    assert initiator["horse"]["bond"] == 28
    assert initiator["horse"]["confidence"] == 38
    assert initiator["horse"]["last_socialized_at"] == "2026-04-01T10:00:00+00:00"
    assert target["horse"]["bond"] == 28
    assert target["horse"]["confidence"] == 38
    assert target["horse"]["last_socialized_at"] is None

    assert [event.get("event_name") for event in telemetry_logger.events] == ["social_interaction_completed"]
    assert telemetry_logger.events[0].get("user_id") == 101
    assert telemetry_logger.events[0].get("guild_id") == 202
    assert telemetry_logger.events[0].get("outcome_id") == "playdate"


def test_socialize_horses_flow_rejects_self_target(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    _adopt_horse(repository=repository, user_id=101, guild_id=202, horse_name="Nova")

    result = socialize_horses_flow(
        repository=repository,
        user_id=101,
        target_user_id=101,
        guild_id=202,
        display_name="Mia",
        target_display_name="Mia",
    )

    assert result.success is False
    assert result.has_initiator_horse is False
    assert result.has_target_horse is False
    assert "cannot playdate with itself" in result.message


def test_socialize_horses_flow_rejects_target_without_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    _adopt_horse(repository=repository, user_id=101, guild_id=202, horse_name="Nova")

    result = socialize_horses_flow(
        repository=repository,
        user_id=101,
        target_user_id=102,
        guild_id=202,
        display_name="Mia",
        target_display_name="Rowan",
    )

    assert result.success is False
    assert result.has_initiator_horse is True
    assert result.has_target_horse is False
    assert "has no adopted horse yet" in result.message


def test_socialize_horses_flow_enforces_cooldown(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    _adopt_horse(repository=repository, user_id=101, guild_id=202, horse_name="Nova")
    _adopt_horse(repository=repository, user_id=102, guild_id=202, horse_name="Luna")

    first = socialize_horses_flow(
        repository=repository,
        user_id=101,
        target_user_id=102,
        guild_id=202,
        display_name="Mia",
        target_display_name="Rowan",
        d10_roll=lambda: 7,
        now_provider=lambda: "2026-04-01T10:00:00+00:00",
    )
    second = socialize_horses_flow(
        repository=repository,
        user_id=101,
        target_user_id=102,
        guild_id=202,
        display_name="Mia",
        target_display_name="Rowan",
        now_provider=lambda: "2026-04-01T10:10:00+00:00",
    )

    assert first.success is True
    assert second.success is False
    assert second.blocked_by_cooldown is True
    assert "Try again in about" in second.message


def test_socialize_horses_flow_allows_reverse_direction_during_initiator_cooldown(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    _adopt_horse(repository=repository, user_id=101, guild_id=202, horse_name="Nova")
    _adopt_horse(repository=repository, user_id=102, guild_id=202, horse_name="Luna")

    first = socialize_horses_flow(
        repository=repository,
        user_id=101,
        target_user_id=102,
        guild_id=202,
        display_name="Mia",
        target_display_name="Rowan",
        now_provider=lambda: "2026-04-01T10:00:00+00:00",
        d10_roll=lambda: 7,
    )
    reverse = socialize_horses_flow(
        repository=repository,
        user_id=102,
        target_user_id=101,
        guild_id=202,
        display_name="Rowan",
        target_display_name="Mia",
        now_provider=lambda: "2026-04-01T10:10:00+00:00",
        d10_roll=lambda: 8,
    )

    assert first.success is True
    assert reverse.success is True
    assert reverse.blocked_by_cooldown is False
