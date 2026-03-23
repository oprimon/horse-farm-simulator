"""Tests for centralized slash command metadata."""

from pferdehof_bot.command_registry import (
    COMMAND_REGISTRY,
    ResponseVisibility,
    get_command_metadata,
)


def test_command_registry_includes_required_slash_surface() -> None:
    required_ids = {
        "start",
        "horse.profile",
        "horse.view",
        "horse.choose",
        "horse.name",
        "horse.rename",
        "greet",
    }

    assert required_ids.issubset(set(COMMAND_REGISTRY.keys()))


def test_command_registry_admin_and_visibility_metadata() -> None:
    rename_metadata = get_command_metadata("horse.rename")
    assert rename_metadata.command_name == "horse"
    assert rename_metadata.subcommand_name == "rename"
    assert rename_metadata.requires_admin is True
    assert rename_metadata.visibility == ResponseVisibility.CHANNEL

    start_metadata = get_command_metadata("start")
    assert start_metadata.command_name == "start"
    assert start_metadata.subcommand_name is None
    assert start_metadata.requires_admin is False
