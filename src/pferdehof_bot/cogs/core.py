"""Core bot commands and baseline setup."""

from pathlib import Path
from typing import Callable, Protocol

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


class _FlowResult(Protocol):
    """Minimal shape every flow result returned by services must provide."""

    @property
    def message(self) -> str:
        ...

    @property
    def presentation(self) -> ResponsePresentation | None:
        ...


class _FollowupFlowResult(_FlowResult, Protocol):
    """Flow result shape required for follow-up action-view resolution."""

    @property
    def player(self) -> dict[str, object] | None:
        ...

    @property
    def has_adopted_horse(self) -> bool:
        ...

    @property
    def blocked_by_readiness(self) -> bool:
        ...


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

    def _resolve_interaction_context(self, interaction: discord.Interaction) -> tuple[int | None, str]:
        """Return common per-interaction context used by service flows."""
        guild_id = interaction.guild.id if interaction.guild is not None else None
        display_name = getattr(interaction.user, "display_name", interaction.user.name)
        return guild_id, display_name

    async def _respond_with_result(
        self,
        *,
        interaction: discord.Interaction,
        command_id: str,
        result: _FlowResult,
        owner_user_id: int | None = None,
        view: discord.ui.View | None = None,
    ) -> None:
        """Canonical response renderer for slash and button-triggered flows."""
        response_view = view
        if response_view is None and owner_user_id is not None and command_id in {"feed", "groom", "rest", "train", "ride"}:
            followup_result = self._as_followup_result(command_id=command_id, result=result)
            if followup_result is not None:
                response_view = self._build_followup_view(
                    command_id=command_id,
                    result=followup_result,
                    owner_user_id=owner_user_id,
                )

        await self._send_response(
            interaction=interaction,
            command_id=command_id,
            message=result.message,
            presentation=result.presentation,
            view=response_view,
        )

    async def _execute_owner_guarded_flow(
        self,
        *,
        interaction: discord.Interaction,
        owner_user_id: int,
        command_id: str,
        wrong_user_message: str,
        flow_runner: Callable[[int | None, str], _FlowResult],
    ) -> None:
        """Run a flow only for owner, then render through the canonical responder."""
        if interaction.user.id != owner_user_id:
            await interaction.response.send_message(wrong_user_message, ephemeral=True)
            return

        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = flow_runner(guild_id, display_name)
        await self._respond_with_result(
            interaction=interaction,
            command_id=command_id,
            result=result,
            owner_user_id=interaction.user.id,
        )

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

            def _disable_all(self) -> None:
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True

            async def on_timeout(self) -> None:
                self._disable_all()

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
                self._disable_all()
                self.stop()
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

    def _build_profile_view(self, *, owner_user_id: int) -> discord.ui.View:
        """Build quick-action buttons for the horse profile embed."""
        cog = self

        class ProfileActionView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=300)

            async def _run(self, interaction: discord.Interaction, flow_fn, command_id: str) -> None:
                await cog._execute_owner_guarded_flow(
                    interaction=interaction,
                    owner_user_id=owner_user_id,
                    command_id=command_id,
                    wrong_user_message="Only the horse's owner can use these actions.",
                    flow_runner=lambda guild_id, display_name: flow_fn(
                        repository=cog._repository,
                        user_id=interaction.user.id,
                        guild_id=guild_id,
                        display_name=display_name,
                        telemetry_logger=cog._telemetry_logger,
                    ),
                )

        view = ProfileActionView()
        actions: list[tuple[str, str, object, discord.ButtonStyle]] = [
            ("🌾 Feed",  "feed",  feed_horse_flow,  discord.ButtonStyle.primary),
            ("🪮 Groom", "groom", groom_horse_flow, discord.ButtonStyle.primary),
            ("😴 Rest",  "rest",  rest_horse_flow,  discord.ButtonStyle.primary),
            ("🎓 Train", "train", train_horse_flow, discord.ButtonStyle.danger),
            ("🐎 Ride",  "ride",  ride_horse_flow,  discord.ButtonStyle.danger),
        ]
        for label, cmd_id, flow_fn, style in actions:
            async def _callback(
                interaction: discord.Interaction,
                _flow=flow_fn,
                _cmd=cmd_id,
            ) -> None:
                await view._run(interaction, _flow, _cmd)

            button = discord.ui.Button(
                label=label,
                style=style,
                custom_id=f"profile_{cmd_id}",
            )
            button.callback = _callback
            view.add_item(button)

        return view

    def _build_recovery_view(self, *, owner_user_id: int) -> discord.ui.View:
        """Build feed/rest quick actions for deferred train/ride states."""
        cog = self

        class RecoveryActionView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=300)

            async def _run(self, interaction: discord.Interaction, flow_fn, command_id: str) -> None:
                await cog._execute_owner_guarded_flow(
                    interaction=interaction,
                    owner_user_id=owner_user_id,
                    command_id=command_id,
                    wrong_user_message="Only the horse's owner can use these actions.",
                    flow_runner=lambda guild_id, display_name: flow_fn(
                        repository=cog._repository,
                        user_id=interaction.user.id,
                        guild_id=guild_id,
                        display_name=display_name,
                        telemetry_logger=cog._telemetry_logger,
                    ),
                )

        view = RecoveryActionView()
        actions: list[tuple[str, str, object]] = [
            ("🌾 Feed", "feed", feed_horse_flow),
            ("😴 Rest", "rest", rest_horse_flow),
        ]
        for label, cmd_id, flow_fn in actions:
            async def _callback(
                interaction: discord.Interaction,
                _flow=flow_fn,
                _cmd=cmd_id,
            ) -> None:
                await view._run(interaction, _flow, _cmd)

            button = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.primary,
                custom_id=f"recovery_{cmd_id}",
            )
            button.callback = _callback
            view.add_item(button)

        return view

    def _build_progression_view(
        self,
        *,
        owner_user_id: int,
        include_train: bool,
        include_ride: bool,
    ) -> discord.ui.View | None:
        """Build follow-up progression actions based on current readiness."""
        if not include_train and not include_ride:
            return None

        cog = self

        class ProgressionActionView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=300)

            async def _run(self, interaction: discord.Interaction, flow_fn, command_id: str) -> None:
                await cog._execute_owner_guarded_flow(
                    interaction=interaction,
                    owner_user_id=owner_user_id,
                    command_id=command_id,
                    wrong_user_message="Only the horse's owner can use these actions.",
                    flow_runner=lambda guild_id, display_name: flow_fn(
                        repository=cog._repository,
                        user_id=interaction.user.id,
                        guild_id=guild_id,
                        display_name=display_name,
                        telemetry_logger=cog._telemetry_logger,
                    ),
                )

        view = ProgressionActionView()
        actions: list[tuple[str, str, object, discord.ButtonStyle]] = []
        if include_train:
            actions.append(("🎓 Train", "train", train_horse_flow, discord.ButtonStyle.danger))
        if include_ride:
            actions.append(("🐎 Ride", "ride", ride_horse_flow, discord.ButtonStyle.danger))

        for label, cmd_id, flow_fn, style in actions:
            async def _callback(
                interaction: discord.Interaction,
                _flow=flow_fn,
                _cmd=cmd_id,
            ) -> None:
                await view._run(interaction, _flow, _cmd)

            button = discord.ui.Button(
                label=label,
                style=style,
                custom_id=f"progression_{cmd_id}",
            )
            button.callback = _callback
            view.add_item(button)

        return view

    def _build_ride_view(self, *, owner_user_id: int) -> discord.ui.View:
        """Build a single quick-action Ride button."""
        ride_view = self._build_progression_view(
            owner_user_id=owner_user_id,
            include_train=False,
            include_ride=True,
        )
        if ride_view is None:
            raise RuntimeError("Expected ride view to include at least one action.")
        return ride_view

    def _build_stable_view(self) -> discord.ui.View:
        """Build stable-level quick actions."""
        cog = self

        class StableView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=300)

        view = StableView()

        async def _profile_callback(interaction: discord.Interaction) -> None:
            await cog._respond_with_profile(interaction)

        profile_button = discord.ui.Button(
            label="🐎 Profile",
            style=discord.ButtonStyle.primary,
            custom_id="stable_profile",
        )
        profile_button.callback = _profile_callback
        view.add_item(profile_button)
        return view

    def _can_ride_from_player(self, player: dict[str, object] | None) -> bool:
        """Return whether a player's horse currently meets ride safety constraints."""
        if player is None or not bool(player.get("adopted", False)):
            return False
        horse = player.get("horse")
        if not isinstance(horse, dict):
            return False
        try:
            energy = int(horse.get("energy") or 0)
            health = int(horse.get("health") or 0)
        except (TypeError, ValueError):
            return False
        return energy >= 30 and health >= 10

    def _can_train_from_player(self, player: dict[str, object] | None) -> bool:
        """Return whether a player's horse currently meets training readiness constraints."""
        if player is None or not bool(player.get("adopted", False)):
            return False
        horse = player.get("horse")
        if not isinstance(horse, dict):
            return False
        try:
            energy = int(horse.get("energy") or 0)
            health = int(horse.get("health") or 0)
        except (TypeError, ValueError):
            return False
        return energy >= 10 and health >= 10

    def _build_followup_view(
        self,
        *,
        command_id: str,
        result: _FlowResult,
        owner_user_id: int,
    ) -> discord.ui.View | None:
        """Build context-sensitive follow-up action views for command results."""
        has_adopted_horse = bool(getattr(result, "has_adopted_horse", False))
        blocked_by_readiness = bool(getattr(result, "blocked_by_readiness", False))
        player = getattr(result, "player", None)

        if command_id in {"feed", "groom", "rest"}:
            return self._build_progression_view(
                owner_user_id=owner_user_id,
                include_train=self._can_train_from_player(player),
                include_ride=self._can_ride_from_player(player),
            )

        if command_id == "train":
            if has_adopted_horse and blocked_by_readiness:
                return self._build_recovery_view(owner_user_id=owner_user_id)
            return self._build_ride_view(owner_user_id=owner_user_id) if self._can_ride_from_player(player) else None

        if command_id == "ride":
            return self._build_recovery_view(owner_user_id=owner_user_id) if has_adopted_horse and blocked_by_readiness else None

        return None

    def _as_followup_result(self, *, command_id: str, result: _FlowResult) -> _FlowResult | None:
        """Return follow-up view input when a result exposes the fields needed for that command."""
        if not hasattr(result, "player"):
            return None
        if not hasattr(result, "has_adopted_horse"):
            return None
        if command_id in {"train", "ride"} and not hasattr(result, "blocked_by_readiness"):
            return None
        return result

    async def _respond_with_profile(self, interaction: discord.Interaction) -> None:
        """Render `/horse profile` response for slash command and profile button flows."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = horse_profile_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
        )
        profile_view = (
            self._build_profile_view(owner_user_id=interaction.user.id)
            if result.has_adopted_horse
            else None
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="horse.profile",
            result=result,
            view=profile_view,
        )

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
        # When an embed is present, suppress the plain-text content so Discord
        # does not render both the text and the card side-by-side.
        if embed is not None and view is not None:
            await interaction.response.send_message(None, embed=embed, view=view, ephemeral=is_ephemeral)
            return
        if embed is not None:
            await interaction.response.send_message(None, embed=embed, ephemeral=is_ephemeral)
            return
        if view is not None:
            await interaction.response.send_message(message, view=view, ephemeral=is_ephemeral)
            return
        await interaction.response.send_message(message, ephemeral=is_ephemeral)

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
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = start_onboarding_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="start",
            result=result,
        )

    @horse_group.command(name="profile", description="Show your current horse profile")
    async def horse_profile(self, interaction: discord.Interaction) -> None:
        """Horse command group for onboarding and horse profile actions."""
        await self._respond_with_profile(interaction)

    @horse_group.command(name="view", description="Show current horse candidates")
    async def horse_view(self, interaction: discord.Interaction) -> None:
        """Display current onboarding horse candidates."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
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
        await self._respond_with_result(
            interaction=interaction,
            command_id="horse.view",
            result=result,
            view=candidate_view,
        )

    @horse_group.command(name="choose", description="Choose one horse candidate by id")
    @app_commands.describe(candidate_id="Candidate id from /horse view: A, B, or C")
    async def horse_choose(self, interaction: discord.Interaction, candidate_id: str) -> None:
        """Choose and lock a horse candidate by id."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = choose_candidate_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            candidate_id=candidate_id,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="horse.choose",
            result=result,
        )

    @horse_group.command(name="name", description="Finalize adoption by naming your horse")
    @app_commands.describe(horse_name="Horse name between 2 and 20 characters")
    async def horse_name(self, interaction: discord.Interaction, horse_name: str) -> None:
        """Name the selected onboarding candidate and finalize adoption."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = name_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            horse_name=horse_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="horse.name",
            result=result,
        )

    @horse_group.command(name="rename", description="Admin-only rename for a player's adopted horse")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(target_user_id="User id of the horse owner", new_name="New horse name")
    async def horse_rename_admin(self, interaction: discord.Interaction, target_user_id: int, new_name: str) -> None:
        """Admin override to rename another player's adopted horse."""
        guild_id, _ = self._resolve_interaction_context(interaction)
        admin_display_name = getattr(interaction.user, "display_name", interaction.user.name)
        result = admin_rename_horse_flow(
            repository=self._repository,
            admin_display_name=admin_display_name,
            target_user_id=target_user_id,
            guild_id=guild_id,
            new_name=new_name,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="horse.rename",
            result=result,
        )

    @app_commands.command(name="greet", description="Greet your adopted horse")
    async def greet(self, interaction: discord.Interaction) -> None:
        """Greet an adopted horse with a lightweight personalized interaction."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = greet_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="greet",
            result=result,
        )

    @app_commands.command(name="feed", description="Feed your adopted horse to restore energy")
    async def feed(self, interaction: discord.Interaction) -> None:
        """Feed an adopted horse and persist the latest care activity."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = feed_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="feed",
            result=result,
            owner_user_id=interaction.user.id,
        )

    @app_commands.command(name="groom", description="Groom your adopted horse to nurture bond and calmness")
    async def groom(self, interaction: discord.Interaction) -> None:
        """Groom an adopted horse and persist the latest care activity."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = groom_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="groom",
            result=result,
            owner_user_id=interaction.user.id,
        )

    @app_commands.command(name="rest", description="Let your adopted horse rest and recover health")
    async def rest(self, interaction: discord.Interaction) -> None:
        """Rest an adopted horse and persist the latest recovery activity."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = rest_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="rest",
            result=result,
            owner_user_id=interaction.user.id,
        )

    @app_commands.command(name="train", description="Train your adopted horse to build skill and confidence")
    async def train(self, interaction: discord.Interaction) -> None:
        """Train an adopted horse with progression, readiness checks, and tradeoffs."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = train_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="train",
            result=result,
            owner_user_id=interaction.user.id,
        )

    @app_commands.command(name="ride", description="Take your adopted horse on a short ride")
    async def ride(self, interaction: discord.Interaction) -> None:
        """Take an adopted horse on a ride and generate a story outcome."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = ride_horse_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            guild_id=guild_id,
            display_name=display_name,
            telemetry_logger=self._telemetry_logger,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="ride",
            result=result,
            owner_user_id=interaction.user.id,
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
        stable_view = self._build_stable_view() if result.has_guild_context else None
        await self._respond_with_result(
            interaction=interaction,
            command_id="stable",
            result=result,
            view=stable_view,
        )


async def setup(bot: commands.Bot) -> None:
    """discord.py extension entry point."""
    await bot.add_cog(CoreCog(bot))
