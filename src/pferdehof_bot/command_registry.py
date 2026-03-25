"""Central command registry for slash command metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ResponseVisibility(StrEnum):
    """Response visibility intent for command replies."""

    CHANNEL = "channel"
    EPHEMERAL = "ephemeral"


@dataclass(frozen=True)
class CommandMetadata:
    """Single source-of-truth metadata for a slash command surface."""

    identifier: str
    command_name: str
    subcommand_name: str | None
    visibility: ResponseVisibility
    requires_admin: bool = False


COMMAND_REGISTRY: dict[str, CommandMetadata] = {
    "start": CommandMetadata(
        identifier="start",
        command_name="start",
        subcommand_name=None,
        visibility=ResponseVisibility.CHANNEL,
    ),
    "horse.profile": CommandMetadata(
        identifier="horse.profile",
        command_name="horse",
        subcommand_name="profile",
        visibility=ResponseVisibility.CHANNEL,
    ),
    "horse.view": CommandMetadata(
        identifier="horse.view",
        command_name="horse",
        subcommand_name="view",
        visibility=ResponseVisibility.CHANNEL,
    ),
    "horse.choose": CommandMetadata(
        identifier="horse.choose",
        command_name="horse",
        subcommand_name="choose",
        visibility=ResponseVisibility.CHANNEL,
    ),
    "horse.name": CommandMetadata(
        identifier="horse.name",
        command_name="horse",
        subcommand_name="name",
        visibility=ResponseVisibility.CHANNEL,
    ),
    "horse.rename": CommandMetadata(
        identifier="horse.rename",
        command_name="horse",
        subcommand_name="rename",
        visibility=ResponseVisibility.CHANNEL,
        requires_admin=True,
    ),
    "greet": CommandMetadata(
        identifier="greet",
        command_name="greet",
        subcommand_name=None,
        visibility=ResponseVisibility.CHANNEL,
    ),
    "feed": CommandMetadata(
        identifier="feed",
        command_name="feed",
        subcommand_name=None,
        visibility=ResponseVisibility.CHANNEL,
    ),
    "groom": CommandMetadata(
        identifier="groom",
        command_name="groom",
        subcommand_name=None,
        visibility=ResponseVisibility.CHANNEL,
    ),
    "rest": CommandMetadata(
        identifier="rest",
        command_name="rest",
        subcommand_name=None,
        visibility=ResponseVisibility.CHANNEL,
    ),
    "train": CommandMetadata(
        identifier="train",
        command_name="train",
        subcommand_name=None,
        visibility=ResponseVisibility.CHANNEL,
    ),
    "ride": CommandMetadata(
        identifier="ride",
        command_name="ride",
        subcommand_name=None,
        visibility=ResponseVisibility.CHANNEL,
    ),
}


def get_command_metadata(identifier: str) -> CommandMetadata:
    """Get metadata for a known command identifier."""
    return COMMAND_REGISTRY[identifier]
