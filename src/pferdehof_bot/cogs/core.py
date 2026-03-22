"""Core bot commands and baseline setup."""

from pathlib import Path

from discord.ext import commands

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services import (
    choose_candidate_flow,
    horse_profile_flow,
    name_horse_flow,
    start_onboarding_flow,
    view_candidates_flow,
)


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

    @commands.group(name="horse", invoke_without_command=True)
    async def horse(self, ctx: commands.Context) -> None:
        """Horse command group for onboarding and horse profile actions."""
        guild_id = ctx.guild.id if ctx.guild is not None else None
        result = horse_profile_flow(
            repository=self._repository,
            user_id=ctx.author.id,
            guild_id=guild_id,
            display_name=ctx.author.display_name,
        )
        await ctx.send(result.message)

    @horse.command(name="view")
    async def horse_view(self, ctx: commands.Context) -> None:
        """Display current onboarding horse candidates."""
        guild_id = ctx.guild.id if ctx.guild is not None else None
        result = view_candidates_flow(
            repository=self._repository,
            user_id=ctx.author.id,
            guild_id=guild_id,
            display_name=ctx.author.display_name,
        )
        await ctx.send(result.message)

    @horse.command(name="choose")
    async def horse_choose(self, ctx: commands.Context, candidate_id: str) -> None:
        """Choose and lock a horse candidate by id."""
        guild_id = ctx.guild.id if ctx.guild is not None else None
        result = choose_candidate_flow(
            repository=self._repository,
            user_id=ctx.author.id,
            guild_id=guild_id,
            display_name=ctx.author.display_name,
            candidate_id=candidate_id,
        )
        await ctx.send(result.message)

    @horse.command(name="name")
    async def horse_name(self, ctx: commands.Context, *, horse_name: str) -> None:
        """Name the selected onboarding candidate and finalize adoption."""
        guild_id = ctx.guild.id if ctx.guild is not None else None
        result = name_horse_flow(
            repository=self._repository,
            user_id=ctx.author.id,
            guild_id=guild_id,
            display_name=ctx.author.display_name,
            horse_name=horse_name,
        )
        await ctx.send(result.message)


async def setup(bot: commands.Bot) -> None:
    """discord.py extension entry point."""
    await bot.add_cog(CoreCog(bot))
