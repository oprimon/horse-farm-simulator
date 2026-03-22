"""Core bot commands and baseline setup.

This cog intentionally keeps only a lightweight command while MVP specs are
implemented incrementally task-by-task.
"""

from discord.ext import commands


class CoreCog(commands.Cog):
    """Core commands available at bot startup."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="hello")
    async def hello(self, ctx: commands.Context) -> None:
        """Simple baseline command for connectivity checks."""
        await ctx.send(f"Hello, {ctx.author.display_name}!")


async def setup(bot: commands.Bot) -> None:
    """discord.py extension entry point."""
    await bot.add_cog(CoreCog(bot))
