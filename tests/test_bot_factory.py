"""Tests for bot factory setup."""

import asyncio

import discord

from pferdehof_bot.bot import CommandSyncSettings, create_bot, sync_application_commands


def test_create_bot_uses_default_prefix():
    bot = create_bot()

    assert bot.command_prefix == "!"


def test_create_bot_accepts_custom_prefix():
    bot = create_bot(command_prefix="/")

    assert bot.command_prefix == "/"


def test_sync_application_commands_off_mode_skips_sync() -> None:
    class FakeTree:
        def __init__(self) -> None:
            self.sync_calls: list[discord.Object | None] = []
            self.copy_calls: list[discord.Object] = []

        async def sync(self, guild: discord.Object | None = None) -> list[object]:
            self.sync_calls.append(guild)
            return []

        def copy_global_to(self, guild: discord.Object) -> None:
            self.copy_calls.append(guild)

    class FakeBot:
        def __init__(self) -> None:
            self.tree = FakeTree()

    fake_bot = FakeBot()
    mode = asyncio.run(sync_application_commands(fake_bot, CommandSyncSettings(mode="off")))

    assert mode == "off"
    assert len(fake_bot.tree.sync_calls) == 0
    assert len(fake_bot.tree.copy_calls) == 0


def test_sync_application_commands_global_syncs_tree() -> None:
    class FakeTree:
        def __init__(self) -> None:
            self.sync_calls: list[discord.Object | None] = []
            self.copy_calls: list[discord.Object] = []

        async def sync(self, guild: discord.Object | None = None) -> list[object]:
            self.sync_calls.append(guild)
            return []

        def copy_global_to(self, guild: discord.Object) -> None:
            self.copy_calls.append(guild)

    class FakeBot:
        def __init__(self) -> None:
            self.tree = FakeTree()

    fake_bot = FakeBot()
    mode = asyncio.run(sync_application_commands(fake_bot, CommandSyncSettings(mode="global")))

    assert mode == "global"
    assert len(fake_bot.tree.sync_calls) == 1
    assert fake_bot.tree.sync_calls[0] is None
    assert len(fake_bot.tree.copy_calls) == 0


def test_sync_application_commands_guild_sync_requires_guild_id() -> None:
    class FakeTree:
        def __init__(self) -> None:
            self.sync_calls: list[discord.Object | None] = []
            self.copy_calls: list[discord.Object] = []

        async def sync(self, guild: discord.Object | None = None) -> list[object]:
            self.sync_calls.append(guild)
            return []

        def copy_global_to(self, guild: discord.Object) -> None:
            self.copy_calls.append(guild)

    class FakeBot:
        def __init__(self) -> None:
            self.tree = FakeTree()

    fake_bot = FakeBot()
    mode = asyncio.run(sync_application_commands(fake_bot, CommandSyncSettings(mode="guild")))

    assert mode == "off"
    assert len(fake_bot.tree.sync_calls) == 0
    assert len(fake_bot.tree.copy_calls) == 0


def test_sync_application_commands_guild_sync_targets_dev_guild() -> None:
    class FakeTree:
        def __init__(self) -> None:
            self.sync_calls: list[discord.Object | None] = []
            self.copy_calls: list[discord.Object] = []

        async def sync(self, guild: discord.Object | None = None) -> list[object]:
            self.sync_calls.append(guild)
            return []

        def copy_global_to(self, guild: discord.Object) -> None:
            self.copy_calls.append(guild)

    class FakeBot:
        def __init__(self) -> None:
            self.tree = FakeTree()

    fake_bot = FakeBot()
    mode = asyncio.run(
        sync_application_commands(
            fake_bot,
            CommandSyncSettings(mode="guild", dev_guild_id=123456),
        )
    )

    assert mode == "guild"
    assert len(fake_bot.tree.copy_calls) == 1
    assert fake_bot.tree.copy_calls[0].id == 123456
    assert len(fake_bot.tree.sync_calls) == 1
    assert fake_bot.tree.sync_calls[0] is not None
    assert fake_bot.tree.sync_calls[0].id == 123456


def test_sync_application_commands_auto_syncs_each_connected_guild() -> None:
    class FakeTree:
        def __init__(self) -> None:
            self.sync_calls: list[discord.Object | None] = []
            self.copy_calls: list[discord.Object] = []

        async def sync(self, guild: discord.Object | None = None) -> list[object]:
            self.sync_calls.append(guild)
            return []

        def copy_global_to(self, guild: discord.Object) -> None:
            self.copy_calls.append(guild)

    class FakeGuild:
        def __init__(self, guild_id: int) -> None:
            self.id = guild_id

    class FakeBot:
        def __init__(self) -> None:
            self.tree = FakeTree()
            self.guilds = [FakeGuild(11), FakeGuild(22)]

    fake_bot = FakeBot()
    mode = asyncio.run(sync_application_commands(fake_bot, CommandSyncSettings(mode="auto")))

    assert mode == "auto"
    assert len(fake_bot.tree.copy_calls) == 2
    assert [guild.id for guild in fake_bot.tree.copy_calls] == [11, 22]
    assert len(fake_bot.tree.sync_calls) == 2
    assert [guild.id for guild in fake_bot.tree.sync_calls if guild is not None] == [11, 22]


def test_sync_application_commands_auto_falls_back_to_global_without_guilds() -> None:
    class FakeTree:
        def __init__(self) -> None:
            self.sync_calls: list[discord.Object | None] = []
            self.copy_calls: list[discord.Object] = []

        async def sync(self, guild: discord.Object | None = None) -> list[object]:
            self.sync_calls.append(guild)
            return []

        def copy_global_to(self, guild: discord.Object) -> None:
            self.copy_calls.append(guild)

    class FakeBot:
        def __init__(self) -> None:
            self.tree = FakeTree()
            self.guilds = []

    fake_bot = FakeBot()
    mode = asyncio.run(sync_application_commands(fake_bot, CommandSyncSettings(mode="auto")))

    assert mode == "auto"
    assert len(fake_bot.tree.copy_calls) == 0
    assert len(fake_bot.tree.sync_calls) == 1
    assert fake_bot.tree.sync_calls[0] is None
