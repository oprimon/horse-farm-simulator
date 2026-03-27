"""Stable roster flow service for guild-wide horse visibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pferdehof_bot.repositories import JsonPlayerRepository

from .flow_utils import emit_telemetry
from .onboarding import PresentationField, ResponsePresentation
from .telemetry import TelemetryLogger


@dataclass(frozen=True)
class StableRosterResult:
    """Result payload for `/stable` command execution."""

    rows: list[dict[str, object]]
    message: str
    has_guild_context: bool
    is_empty: bool
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


def stable_roster_flow(
    repository: JsonPlayerRepository,
    guild_id: int | None,
    display_name: str,
    owner_display_name_resolver: Callable[[int], str | None] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
    user_id: int | None = None,
) -> StableRosterResult:
    """Render the adopted-horse roster for the current guild."""
    if guild_id is None:
        message = (
            "The stable roster needs a server stable to look at. "
            "Use `/stable` from a guild channel."
        )
        return StableRosterResult(
            rows=[],
            message=message,
            has_guild_context=False,
            is_empty=True,
            presentation=_build_presentation(
                title="Stable Unavailable",
                description=message,
                accent="warning",
            ),
        )

    raw_rows = repository.list_adopted_horses_by_guild(guild_id=guild_id)
    if not raw_rows:
        message = (
            "The stable is still quiet in this server. "
            "No horses have been adopted here yet. Use `/start` to welcome the first one."
        )
        return StableRosterResult(
            rows=[],
            message=message,
            has_guild_context=True,
            is_empty=True,
            presentation=_build_presentation(
                title="Stable Is Quiet",
                description=message,
                accent="info",
            ),
        )

    rows: list[dict[str, object]] = []
    lines = ["Here is the current stable roster:"]
    for raw_row in raw_rows:
        owner_user_id = int(raw_row["owner_user_id"])
        owner_display_name = _resolve_owner_display_name(
            owner_user_id=owner_user_id,
            owner_display_name_resolver=owner_display_name_resolver,
        )
        row = {
            "horse_id": int(raw_row["horse_id"]),
            "horse_name": str(raw_row["horse_name"]),
            "owner_user_id": owner_user_id,
            "owner_display_name": owner_display_name,
            "guild_id": guild_id,
        }
        rows.append(row)
        lines.append(
            f"#{row['horse_id']} | {row['horse_name']} | Owner: {row['owner_display_name']}"
        )

    lines.append("Use `/horse profile` to check on your own companion.")
    if user_id is not None:
        emit_telemetry(
            telemetry_logger=telemetry_logger,
            event_name="viewed_stable",
            user_id=user_id,
            guild_id=guild_id,
        )
    return StableRosterResult(
        rows=rows,
        message="\n".join(lines),
        has_guild_context=True,
        is_empty=False,
        presentation=_build_presentation(
            title="Server Stable Roster",
            description="Here are the horses currently adopted in this server.",
            accent="info",
            fields=tuple(
                PresentationField(
                    name=f"#{row['horse_id']} - {row['horse_name']}",
                    value=f"Owner: {row['owner_display_name']}",
                )
                for row in rows
            ),
            footer="Use `/horse profile` to check on your own companion.",
        ),
    )


def _resolve_owner_display_name(
    owner_user_id: int,
    owner_display_name_resolver: Callable[[int], str | None] | None,
) -> str:
    if owner_display_name_resolver is None:
        return f"Unknown rider ({owner_user_id})"

    owner_display_name = owner_display_name_resolver(owner_user_id)
    if owner_display_name is None:
        return f"Unknown rider ({owner_user_id})"

    normalized_name = str(owner_display_name).strip()
    if not normalized_name:
        return f"Unknown rider ({owner_user_id})"

    return normalized_name
