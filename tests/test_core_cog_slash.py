"""Tests for core slash command registration and transport migration."""

import asyncio

import discord

from pferdehof_bot.bot import create_bot, load_extensions


def test_core_cog_registers_slash_commands() -> None:
    bot = create_bot()
    asyncio.run(load_extensions(bot))

    commands_by_name = {command.name: command for command in bot.tree.get_commands()}
    assert "start" in commands_by_name
    assert "greet" in commands_by_name
    assert "feed" in commands_by_name
    assert "groom" in commands_by_name
    assert "rest" in commands_by_name
    assert "train" in commands_by_name
    assert "horse" in commands_by_name

    horse_group = commands_by_name["horse"]
    assert isinstance(horse_group, discord.app_commands.Group)

    subcommands_by_name = {command.name: command for command in horse_group.commands}
    assert "profile" in subcommands_by_name
    assert "view" in subcommands_by_name
    assert "choose" in subcommands_by_name
    assert "name" in subcommands_by_name
    assert "rename" in subcommands_by_name

    rename_command = subcommands_by_name["rename"]
    assert rename_command.default_permissions is not None
    assert rename_command.default_permissions.administrator is True


def test_prefix_command_handlers_are_not_registered_after_migration() -> None:
    bot = create_bot()
    asyncio.run(load_extensions(bot))

    assert bot.get_command("start") is None
    assert bot.get_command("greet") is None
    assert bot.get_command("feed") is None
    assert bot.get_command("groom") is None
    assert bot.get_command("rest") is None
    assert bot.get_command("train") is None
    assert bot.get_command("horse") is None
