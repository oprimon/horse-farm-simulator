"""Core bot commands and baseline setup."""

from pathlib import Path

from discord.ext import commands

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services import start_onboarding_flow


DEFAULT_PLAYER_STORAGE_PATH = Path("data") / "players.json"


class CoreCog(commands.Cog):
    """Core commands available at bot startup."""

    def __init__(
        self,
        bot: commands.Bot,
        repository: JsonPlayerRepository | None = None,
    ) -> None:
        self.bot = bot
        self._repository = repository or JsonPlayerRepository(storage_path=DEFAULT_PLAYER_STORAGE_PATH)

    @commands.command(name="start")
    async def start(self, ctx: commands.Context) -> None:
        """Start or resume player onboarding for horse adoption."""
        guild_id = ctx.guild.id if ctx.guild is not None else None
        result = start_onboarding_flow(
            repository=self._repository,
            user_id=ctx.author.id,
            guild_id=guild_id,
            display_name=ctx.author.display_name,
        )
        await ctx.send(result.message)


async def setup(bot: commands.Bot) -> None:
    """discord.py extension entry point."""
    await bot.add_cog(CoreCog(bot))
