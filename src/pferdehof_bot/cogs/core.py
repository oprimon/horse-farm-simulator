"""Core bot commands and baseline setup."""

from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from pferdehof_bot.command_registry import ResponseVisibility, get_command_metadata
from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services.onboarding import ResponsePresentation
from pferdehof_bot.services import (
    FileTelemetryLogger,
    admin_rename_horse_flow,
    choose_candidate_flow,
    feed_horse_flow,
    greet_horse_flow,
    groom_horse_flow,
    horse_profile_flow,
    name_horse_flow,
    rest_horse_flow,
    ride_horse_flow,
    stable_roster_flow,
    start_onboarding_flow,
    train_horse_flow,
    view_candidates_flow,
)


DEFAULT_PLAYER_STORAGE_PATH = Path("data") / "players.json"
DEFAULT_TELEMETRY_STORAGE_PATH = Path("data") / "telemetry.jsonl"


class CoreCog(commands.Cog):
    """Core commands available at bot startup."""

    horse_group = app_commands.Group(name="horse", description="Horse onboarding and profile commands")

    def __init__(
        self,
        bot: commands.Bot,
        repository: JsonPlayerRepository | None = None,
        telemetry_logger: FileTelemetryLogger | None = None,
    ) -> None:
        self.bot = bot
        self._repository = repository or JsonPlayerRepository(storage_path=DEFAULT_PLAYER_STORAGE_PATH)
        self._telemetry_logger = telemetry_logger or FileTelemetryLogger(DEFAULT_TELEMETRY_STORAGE_PATH)

    def _build_embed(self, presentation: ResponsePresentation) -> discord.Embed:
        """Build a Discord embed from a service presentation payload."""
        accent = (presentation.accent or "").lower()
        color_by_accent: dict[str, discord.Color] = {
            "success": discord.Color.green(),
            "warning": discord.Color.orange(),
            "error": discord.Color.red(),
            "info": discord.Color.blurple(),
        }
        embed = discord.Embed(
            title=presentation.title,
            description=presentation.description,
            color=color_by_accent.get(accent, discord.Color.light_grey()),
        )
        for field in presentation.fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        if presentation.footer is not None:
            embed.set_footer(text=presentation.footer)
        return embed

    def _build_candidate_view(
        self,
        *,
        candidates: list[dict[str, object]],
        owner_user_id: int,
    ) -> discord.ui.View | None:
        """Build a candidate-selection button row for onboarding sessions."""
        candidate_ids: list[str] = []
        for candidate in candidates:
            candidate_id = str(candidate.get("id", "")).upper().strip()
            if candidate_id in {"A", "B", "C"}:
                candidate_ids.append(candidate_id)

        if not candidate_ids:
            return None

        cog = self

        class ChooseCandidateView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=300)

            async def _handle_choice(self, interaction: discord.Interaction, candidate_id: str) -> None:
                if interaction.user.id != owner_user_id:
                    await interaction.response.send_message(
                        "Only the player who opened these candidates can choose from this panel.",
                        ephemeral=True,
                    )
                    return

                guild_id = interaction.guild.id if interaction.guild is not None else None
                display_name = getattr(interaction.user, "display_name", interaction.user.name)
                result = choose_candidate_flow(
                    repository=cog._repository,
                    user_id=interaction.user.id,
                    guild_id=guild_id,
                    display_name=display_name,
                    candidate_id=candidate_id,
                    telemetry_logger=cog._telemetry_logger,
                )
                await cog._send_response(
                    interaction=interaction,
                    command_id="horse.choose",
                    message=result.message,
                    presentation=result.presentation,
                )

        view = ChooseCandidateView()
        for candidate_id in sorted(set(candidate_ids)):

            async def _callback(interaction: discord.Interaction, selected_id: str = candidate_id) -> None:
                await view._handle_choice(interaction=interaction, candidate_id=selected_id)

            button = discord.ui.Button(
                label=f"Adopt {candidate_id}",
                style=discord.ButtonStyle.primary,
                custom_id=f"horse_choose_{candidate_id}",
            )
            button.callback = _callback
            view.add_item(button)

        return view

    async def _send_response(
        self,
        interaction: discord.Interaction,
        command_id: str,
        message: str,
        presentation: ResponsePresentation | None = None,
        view: discord.ui.View | None = None,
    ) -> None:
        """Send a response based on command visibility metadata."""
        metadata = get_command_metadata(command_id)
        is_ephemeral = metadata.visibility == ResponseVisibility.EPHEMERAL
        embed = self._build_embed(presentation) if presentation is not None else None
        await interaction.response.send_message(message, embed=embed, view=view, ephemeral=is_ephemeral)

    async def _build_owner_display_name_map(
        self,
        guild: discord.Guild,
        owner_user_ids: set[int],
        interaction_user_id: int,
        interaction_display_name: str,
    ) -> dict[int, str]:
        """Resolve owner names with guild-display priority and API fallback."""
        resolved_names: dict[int, str] = {}
        for owner_user_id in owner_user_ids:
            if owner_user_id == interaction_user_id:
                resolved_names[owner_user_id] = interaction_display_name
                continue

            member = guild.get_member(owner_user_id)
            if member is not None:
                resolved_names[owner_user_id] = getattr(member, "display_name", member.name)
                continue

            try:
                fetched_member = await guild.fetch_member(owner_user_id)
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                continue

            resolved_names[owner_user_id] = getattr(fetched_member, "display_name", fetched_member.name)

        return resolved_names

    @app_commands.command(name="start", description="Start or resume horse adoption onboarding")
    async def start(self, interaction: discord.Interaction) -> None:
        """Start or resume player onboarding for horse adoption."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = start_onboarding_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="start",
            message=result.message,
            presentation=result.presentation,
        )

    @horse_group.command(name="profile", description="Show your current horse profile")
    async def horse_profile(self, interaction: discord.Interaction) -> None:
        """Horse command group for onboarding and horse profile actions."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = horse_profile_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
        )
        await self._send_response(
            interaction=interaction,
            command_id="horse.profile",
            message=result.message,
            presentation=result.presentation,
        )

    @horse_group.command(name="view", description="Show current horse candidates")
    async def horse_view(self, interaction: discord.Interaction) -> None:
        """Display current onboarding horse candidates."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = view_candidates_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        candidates = []
        if result.player is not None and result.has_active_session and not result.already_adopted:
            onboarding_session = result.player.get("onboarding_session") or {}
            raw_candidates = onboarding_session.get("candidates")
            if isinstance(raw_candidates, list):
                candidates = [candidate for candidate in raw_candidates if isinstance(candidate, dict)]

        candidate_view = self._build_candidate_view(candidates=candidates, owner_user_id=interaction.user.id)
        await self._send_response(
            interaction=interaction,
            command_id="horse.view",
            message=result.message,
            presentation=result.presentation,
            view=candidate_view,
        )

    @horse_group.command(name="choose", description="Choose one horse candidate by id")
    @app_commands.describe(candidate_id="Candidate id from /horse view: A, B, or C")
    async def horse_choose(self, interaction: discord.Interaction, candidate_id: str) -> None:
        """Choose and lock a horse candidate by id."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = choose_candidate_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            candidate_id=candidate_id,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="horse.choose",
            message=result.message,
            presentation=result.presentation,
        )

    @horse_group.command(name="name", description="Finalize adoption by naming your horse")
    @app_commands.describe(horse_name="Horse name between 2 and 20 characters")
    async def horse_name(self, interaction: discord.Interaction, horse_name: str) -> None:
        """Name the selected onboarding candidate and finalize adoption."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = name_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            horse_name=horse_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="horse.name",
            message=result.message,
            presentation=result.presentation,
        )

    @horse_group.command(name="rename", description="Admin-only rename for a player's adopted horse")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(target_user_id="User id of the horse owner", new_name="New horse name")
    async def horse_rename_admin(self, interaction: discord.Interaction, target_user_id: int, new_name: str) -> None:
        """Admin override to rename another player's adopted horse."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        admin_display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = admin_rename_horse_flow(
            repository=self._repository,
            admin_display_name=admin_display_name,
            target_user_id=target_user_id,
            guild_id=guild_id,
            new_name=new_name,
        )
        await self._send_response(
            interaction=interaction,
            command_id="horse.rename",
            message=result.message,
            presentation=result.presentation,
        )

    @app_commands.command(name="greet", description="Greet your adopted horse")
    async def greet(self, interaction: discord.Interaction) -> None:
        """Greet an adopted horse with a lightweight personalized interaction."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = greet_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="greet",
            message=result.message,
            presentation=result.presentation,
        )

    @app_commands.command(name="feed", description="Feed your adopted horse to restore energy")
    async def feed(self, interaction: discord.Interaction) -> None:
        """Feed an adopted horse and persist the latest care activity."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = feed_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="feed",
            message=result.message,
            presentation=result.presentation,
        )

    @app_commands.command(name="groom", description="Groom your adopted horse to nurture bond and calmness")
    async def groom(self, interaction: discord.Interaction) -> None:
        """Groom an adopted horse and persist the latest care activity."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = groom_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="groom",
            message=result.message,
            presentation=result.presentation,
        )

    @app_commands.command(name="rest", description="Let your adopted horse rest and recover health")
    async def rest(self, interaction: discord.Interaction) -> None:
        """Rest an adopted horse and persist the latest recovery activity."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = rest_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="rest",
            message=result.message,
            presentation=result.presentation,
        )

    @app_commands.command(name="train", description="Train your adopted horse to build skill and confidence")
    async def train(self, interaction: discord.Interaction) -> None:
        """Train an adopted horse with progression, readiness checks, and tradeoffs."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = train_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="train",
            message=result.message,
            presentation=result.presentation,
        )

    @app_commands.command(name="ride", description="Take your adopted horse on a short ride")
    async def ride(self, interaction: discord.Interaction) -> None:
        """Take an adopted horse on a ride and generate a story outcome."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = ride_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._send_response(
            interaction=interaction,
            command_id="ride",
            message=result.message,
            presentation=result.presentation,
        )

    @app_commands.command(name="stable", description="Show the adopted horses in this server's stable")
    async def stable(self, interaction: discord.Interaction) -> None:
        """Render the adopted-horse roster for the current guild."""
        guild = interaction.guild
        guild_id = guild.id if guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)

        owner_display_names: dict[int, str] = {}
        if guild is not None and guild_id is not None:
            raw_rows = self._repository.list_adopted_horses_by_guild(guild_id=guild_id)
            owner_user_ids = {int(raw_row["owner_user_id"]) for raw_row in raw_rows}
            owner_display_names = await self._build_owner_display_name_map(
                guild=guild,
                owner_user_ids=owner_user_ids,
                interaction_user_id=interaction.user.id,
                interaction_display_name=display_name,
            )

        def owner_display_name_resolver(owner_user_id: int) -> str | None:
            return owner_display_names.get(owner_user_id)

        result = stable_roster_flow(
            repository=self._repository,
            guild_id=guild_id,
            display_name=display_name,
            owner_display_name_resolver=owner_display_name_resolver,
            telemetry_logger=self._telemetry_logger,
            user_id=interaction.user.id,
        )
        await self._send_response(
            interaction=interaction,
            command_id="stable",
            message=result.message,
            presentation=result.presentation,
        )


async def setup(bot: commands.Bot) -> None:
    """discord.py extension entry point."""
    await bot.add_cog(CoreCog(bot))
