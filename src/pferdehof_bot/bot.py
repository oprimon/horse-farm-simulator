"""Bot factory and startup helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Sequence

import discord
from discord.ext import commands


DEFAULT_EXTENSIONS: tuple[str, ...] = (
    "pferdehof_bot.cogs.core",
)


@dataclass(frozen=True)
class CommandSyncSettings:
    """Configuration for startup slash-command synchronization."""

    mode: str = "global"
    dev_guild_id: int | None = None


def _normalized_sync_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized in {"off", "global", "guild", "auto"}:
        return normalized
    return "global"


async def sync_application_commands(bot: commands.Bot, settings: CommandSyncSettings) -> str:
    """Synchronize app commands based on startup settings.

    Returns the effective sync mode used at runtime.
    """
    mode = _normalized_sync_mode(settings.mode)
    if mode == "off":
        return mode

    if mode == "guild":
        if settings.dev_guild_id is None:
            return "off"
        guild_object = discord.Object(id=settings.dev_guild_id)
        bot.tree.copy_global_to(guild=guild_object)
        await bot.tree.sync(guild=guild_object)
        return mode

    if mode == "global":
        # Remove stale guild-scoped command copies so only global commands remain.
        for guild in tuple(bot.guilds):
            guild_object = discord.Object(id=guild.id)
            bot.tree.clear_commands(guild=guild_object)
            await bot.tree.sync(guild=guild_object)

        await bot.tree.sync()
        return mode

    if mode == "auto":
        guilds = tuple(bot.guilds)
        if len(guilds) == 0:
            await bot.tree.sync()
            return mode

        for guild in guilds:
            guild_object = discord.Object(id=guild.id)
            bot.tree.copy_global_to(guild=guild_object)
            await bot.tree.sync(guild=guild_object)
        return mode

    await bot.tree.sync()
    return mode


def create_bot(
    command_prefix=commands.when_mentioned,
    command_sync_settings: CommandSyncSettings | None = None,
) -> commands.Bot:
    """Create a configured commands.Bot instance."""
    intents = discord.Intents.default()
    intents.message_content = False

    bot = commands.Bot(command_prefix=command_prefix, intents=intents)
    sync_settings = command_sync_settings or CommandSyncSettings()
    command_sync_completed = False
    command_sync_lock = asyncio.Lock()

    @bot.event
    async def on_ready() -> None:
        nonlocal command_sync_completed
        username = str(bot.user) if bot.user is not None else "Unknown"
        user_id = bot.user.id if bot.user is not None else "Unknown"
        print(f"Logged in as {username} (ID: {user_id})")
        print("------")
        if command_sync_completed:
            print("Command sync mode: skipped (already synced this process)")
            return

        async with command_sync_lock:
            if command_sync_completed:
                print("Command sync mode: skipped (already synced this process)")
                return

            sync_mode = await sync_application_commands(bot, sync_settings)
            command_sync_completed = True
            print(f"Command sync mode: {sync_mode}")

    return bot


async def load_extensions(bot: commands.Bot, extensions: Sequence[str] = DEFAULT_EXTENSIONS) -> None:
    """Load configured command extensions."""
    for extension in extensions:
        await bot.load_extension(extension)
