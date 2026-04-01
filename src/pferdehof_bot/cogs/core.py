"""Core bot commands and baseline setup."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol

import discord
from discord import app_commands
from discord.ext import commands

from pferdehof_bot.cogs.shared.context import build_owner_display_name_map, resolve_interaction_context
from pferdehof_bot.cogs.shared.responder import build_embed, send_response
from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services.care import feed_horse_flow, groom_horse_flow, rest_horse_flow
from pferdehof_bot.services.lifecycle import (
    admin_rename_horse_flow,
    choose_candidate_flow,
    greet_horse_flow,
    horse_profile_flow,
    name_horse_flow,
    start_onboarding_flow,
    view_candidates_flow,
)
from pferdehof_bot.services.presentation_models import ResponsePresentation
from pferdehof_bot.services.progression import can_ride_player, can_train_player, ride_horse_flow, train_horse_flow
from pferdehof_bot.services.social import SOCIALIZE_COOLDOWN_SECONDS, SocializeHorseResult, socialize_horses_flow
from pferdehof_bot.services.stable import stable_roster_flow
from pferdehof_bot.services.telemetry import FileTelemetryLogger


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
        return build_embed(presentation)

    def _resolve_interaction_context(self, interaction: discord.Interaction) -> tuple[int | None, str]:
        """Return common per-interaction context used by service flows."""
        return resolve_interaction_context(interaction)

    async def _respond_with_result(
        self,
        *,
        interaction: discord.Interaction,
        command_id: str,
        result: _FlowResult,
        owner_user_id: int | None = None,
        view: discord.ui.View | None = None,
        content_override: str | None = None,
        allowed_mentions: discord.AllowedMentions | None = None,
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
            content_override=content_override,
            allowed_mentions=allowed_mentions,
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
        if not await self._guard_interaction_user(
            interaction=interaction,
            allowed_user_ids={owner_user_id},
            wrong_user_message=wrong_user_message,
        ):
            return

        guild_id, display_name = self._resolve_interaction_context(interaction)
        result = flow_runner(guild_id, display_name)
        await self._respond_with_result(
            interaction=interaction,
            command_id=command_id,
            result=result,
            owner_user_id=interaction.user.id,
        )

    async def _guard_interaction_user(
        self,
        *,
        interaction: discord.Interaction,
        allowed_user_ids: set[int],
        wrong_user_message: str,
    ) -> bool:
        """Return whether the interaction user is allowed for this action and emit guard message otherwise."""
        if interaction.user.id in allowed_user_ids:
            return True

        await interaction.response.send_message(wrong_user_message, ephemeral=True)
        return False

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
                if not await cog._guard_interaction_user(
                    interaction=interaction,
                    allowed_user_ids={owner_user_id},
                    wrong_user_message="Only the player who opened these candidates can choose from this panel.",
                ):
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

    def _build_post_ride_profile_view(self, *, owner_user_id: int) -> discord.ui.View:
        """Build a single quick-action Profile button for successful ride results."""
        cog = self

        class PostRideProfileView(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=300)

            async def _run(self, interaction: discord.Interaction) -> None:
                if not await cog._guard_interaction_user(
                    interaction=interaction,
                    allowed_user_ids={owner_user_id},
                    wrong_user_message="Only the horse's owner can use this action.",
                ):
                    return

                await cog._respond_with_profile(interaction)

        view = PostRideProfileView()

        async def _callback(interaction: discord.Interaction) -> None:
            await view._run(interaction)

        button = discord.ui.Button(
            label="🐎 Profile",
            style=discord.ButtonStyle.primary,
            custom_id="post_ride_profile",
        )
        button.callback = _callback
        view.add_item(button)
        return view

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
        return can_ride_player(player)

    def _can_train_from_player(self, player: dict[str, object] | None) -> bool:
        """Return whether a player's horse currently meets training readiness constraints."""
        return can_train_player(player)

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
            if has_adopted_horse and blocked_by_readiness:
                return self._build_recovery_view(owner_user_id=owner_user_id)
            return self._build_post_ride_profile_view(owner_user_id=owner_user_id) if has_adopted_horse else None

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
        content_override: str | None = None,
        allowed_mentions: discord.AllowedMentions | None = None,
    ) -> None:
        """Send a response based on command visibility metadata."""
        await send_response(
            interaction=interaction,
            command_id=command_id,
            message=message,
            presentation=presentation,
            view=view,
            content_override=content_override,
            allowed_mentions=allowed_mentions,
        )

    def _parse_stable_horse_id(self, raw_horse_id: str) -> int | None:
        """Parse and validate a stable horse id input from slash command arguments."""
        normalized = str(raw_horse_id).strip()
        if not normalized:
            return None

        try:
            parsed = int(normalized)
        except ValueError:
            return None

        return parsed if parsed > 0 else None

    def _build_playdate_target_mention(
        self,
        *,
        result: SocializeHorseResult,
        target_user_id: int,
        now_timestamp: str | None = None,
    ) -> tuple[str | None, discord.AllowedMentions | None]:
        """Build smart mention payload for successful playdates without noisy ping spam."""
        if not result.success:
            return None, None

        target_horse = (result.target_player or {}).get("horse") if result.target_player is not None else None
        target_last_socialized_at = None
        if isinstance(target_horse, dict):
            target_last_socialized_at = target_horse.get("last_socialized_at")

        if self._is_timestamp_within_window(
            timestamp=target_last_socialized_at,
            seconds=SOCIALIZE_COOLDOWN_SECONDS,
            now_timestamp=now_timestamp,
        ):
            return None, None

        mention = f"<@{target_user_id}> your horse just joined a playdate."
        return mention, discord.AllowedMentions(users=True, roles=False, everyone=False, replied_user=False)

    def _is_timestamp_within_window(
        self,
        *,
        timestamp: object,
        seconds: int,
        now_timestamp: str | None = None,
    ) -> bool:
        """Return whether a timestamp falls within the trailing cooldown window from now."""
        parsed_timestamp = self._parse_iso_timestamp(timestamp)
        reference_timestamp = self._parse_iso_timestamp(now_timestamp) if now_timestamp is not None else datetime.now(UTC)
        if parsed_timestamp is None or reference_timestamp is None:
            return False
        return (reference_timestamp - parsed_timestamp).total_seconds() < seconds

    def _parse_iso_timestamp(self, raw_timestamp: object) -> datetime | None:
        """Normalize optional text timestamps into UTC-aware datetime objects."""
        if raw_timestamp is None:
            return None

        text = str(raw_timestamp).strip()
        if not text:
            return None

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    async def _build_owner_display_name_map(
        self,
        guild: discord.Guild,
        owner_user_ids: set[int],
        interaction_user_id: int,
        interaction_display_name: str,
    ) -> dict[int, str]:
        """Resolve owner names with guild-display priority and API fallback."""
        return await build_owner_display_name_map(
            guild=guild,
            owner_user_ids=owner_user_ids,
            interaction_user_id=interaction_user_id,
            interaction_display_name=interaction_display_name,
        )

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

    @app_commands.command(name="playdate", description="Let your horse socialize with another horse from the stable")
    @app_commands.describe(target_horse_id="Horse id from /stable (for example: 2)")
    async def playdate(self, interaction: discord.Interaction, target_horse_id: str) -> None:
        """Run a cooperative horse playdate targeting a stable horse id."""
        guild_id, display_name = self._resolve_interaction_context(interaction)
        if guild_id is None:
            result = socialize_horses_flow(
                repository=self._repository,
                user_id=interaction.user.id,
                target_user_id=interaction.user.id,
                guild_id=None,
                display_name=display_name,
                target_display_name=display_name,
                telemetry_logger=self._telemetry_logger,
            )
            await self._respond_with_result(
                interaction=interaction,
                command_id="playdate",
                result=result,
                owner_user_id=interaction.user.id,
            )
            return

        horse_id = self._parse_stable_horse_id(target_horse_id)
        if horse_id is None:
            await self._send_response(
                interaction=interaction,
                command_id="playdate",
                message="Please provide a valid horse id from `/stable`, such as `1` or `2`.",
            )
            return

        target_horse_row = self._repository.get_adopted_horse_by_id(guild_id=guild_id, horse_id=horse_id)
        if target_horse_row is None:
            await self._send_response(
                interaction=interaction,
                command_id="playdate",
                message=f"No horse with id #{horse_id} was found in this server's stable. Use `/stable` to view valid ids.",
            )
            return

        target_user_id = int(target_horse_row["owner_user_id"])
        target_display_name = f"Rider {target_user_id}"
        guild = interaction.guild
        if guild is not None:
            owner_display_names = await self._build_owner_display_name_map(
                guild=guild,
                owner_user_ids={target_user_id},
                interaction_user_id=interaction.user.id,
                interaction_display_name=display_name,
            )
            target_display_name = owner_display_names.get(target_user_id, target_display_name)

        result = socialize_horses_flow(
            repository=self._repository,
            user_id=interaction.user.id,
            target_user_id=target_user_id,
            guild_id=guild_id,
            display_name=display_name,
            target_display_name=target_display_name,
            telemetry_logger=self._telemetry_logger,
        )
        mention_content, allowed_mentions = self._build_playdate_target_mention(
            result=result,
            target_user_id=target_user_id,
        )
        await self._respond_with_result(
            interaction=interaction,
            command_id="playdate",
            result=result,
            owner_user_id=interaction.user.id,
            content_override=mention_content,
            allowed_mentions=allowed_mentions,
        )

    @playdate.autocomplete("target_horse_id")
    async def playdate_horse_id_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Suggest stable horse ids with horse and owner context for `/playdate`."""
        guild = interaction.guild
        if guild is None:
            return []

        guild_id = guild.id
        raw_rows = self._repository.list_adopted_horses_by_guild(guild_id=guild_id)
        owner_user_ids = {int(row["owner_user_id"]) for row in raw_rows}
        interaction_display_name = getattr(interaction.user, "display_name", interaction.user.name)
        owner_display_names = await self._build_owner_display_name_map(
            guild=guild,
            owner_user_ids=owner_user_ids,
            interaction_user_id=interaction.user.id,
            interaction_display_name=interaction_display_name,
        )

        normalized_current = str(current).strip().lower()
        choices: list[app_commands.Choice[str]] = []
        for row in raw_rows:
            horse_id = int(row["horse_id"])
            owner_user_id = int(row["owner_user_id"])
            horse_name = str(row["horse_name"])
            owner_name = owner_display_names.get(owner_user_id, f"Rider {owner_user_id}")
            label = f"#{horse_id} | {horse_name} | {owner_name}"
            if normalized_current and normalized_current not in label.lower():
                continue

            choices.append(app_commands.Choice(name=label[:100], value=str(horse_id)))
            if len(choices) >= 25:
                break

        return choices

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
