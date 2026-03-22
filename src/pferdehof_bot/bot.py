"""Bot factory and startup helpers."""

from typing import Sequence

import discord
from discord.ext import commands


DEFAULT_EXTENSIONS: tuple[str, ...] = (
    "pferdehof_bot.cogs.core",
)


def create_bot(command_prefix: str = "!") -> commands.Bot:
    """Create a configured commands.Bot instance."""
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix=command_prefix, intents=intents)

    @bot.event
    async def on_ready() -> None:
        if bot.user is None:
            return
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
        print("------")

    return bot


async def load_extensions(bot: commands.Bot, extensions: Sequence[str] = DEFAULT_EXTENSIONS) -> None:
    """Load configured command extensions."""
    for extension in extensions:
        await bot.load_extension(extension)
