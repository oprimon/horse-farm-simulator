"""Onboarding flow services for horse adoption journey commands."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable

_logger = logging.getLogger(__name__)

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.repositories.player_repository import CandidateRecord, PlayerRecord

from .candidate_generator import generate_candidate_horses
from .flow_utils import (
    emit_telemetry as _emit_telemetry,
)
from .moderation import contains_blocked_name_term, validate_horse_name
from .state_presentation import build_horse_state_presentation
from .telemetry import TelemetryLogger


@dataclass(frozen=True)
class PresentationField:
    """Single field entry for structured Discord response rendering."""

    name: str
    value: str
    inline: bool = False


@dataclass(frozen=True)
class ResponsePresentation:
    """Structured presentation payload used by Discord transport renderers."""

    title: str
    description: str
    fields: tuple[PresentationField, ...] = ()
    accent: str | None = None
    footer: str | None = None


@dataclass(frozen=True)
class StartOnboardingResult:
    """Result payload for `/start` onboarding flow execution."""

    player: PlayerRecord
    message: str
    already_adopted: bool
    reused_active_session: bool
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class ViewCandidatesResult:
    """Result payload for `/horse view` command execution."""

    player: PlayerRecord | None
    message: str
    has_active_session: bool
    already_adopted: bool
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class ChooseCandidateResult:
    """Result payload for `/horse choose <id>` command execution."""

    player: PlayerRecord | None
    message: str
    selected_candidate_id: str | None
    selection_locked: bool
    invalid_candidate_id: bool
    has_active_session: bool
    already_adopted: bool
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class NameHorseResult:
    """Result payload for `/horse name <name>` command execution."""

    player: PlayerRecord | None
    message: str
    finalized: bool
    invalid_name: bool
    has_active_session: bool
    has_chosen_candidate: bool
    already_adopted: bool
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class HorseProfileResult:
    """Result payload for `/horse` profile command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class GreetHorseResult:
    """Result payload for `/greet` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class StableRosterResult:
    """Result payload for `/stable` command execution."""

    rows: list[dict[str, object]]
    message: str
    has_guild_context: bool
    is_empty: bool
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class AdminRenameHorseResult:
    """Result payload for admin `horse rename` override command."""

    player: PlayerRecord | None
    message: str
    renamed: bool
    invalid_name: bool
    target_has_horse: bool
    presentation: ResponsePresentation | None = None


def _build_presentation(
    title: str,
    description: str,
    *,
    accent: str = "info",
    footer: str | None = None,
    fields: tuple[PresentationField, ...] = (),
) -> ResponsePresentation:
    """Create a standardized response presentation payload."""
    return ResponsePresentation(
        title=title,
        description=description,
        fields=fields,
        accent=accent,
        footer=footer,
    )


def start_onboarding_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    candidate_seed: int | str | None = None,
    candidate_generator: Callable[[int | str | None], list[CandidateRecord]] = generate_candidate_horses,
    telemetry_logger: TelemetryLogger | None = None,
) -> StartOnboardingResult:
    """Start onboarding for a player or reuse existing active onboarding."""
    existing_player = repository.get_player(user_id=user_id, guild_id=guild_id)

    if existing_player is not None and bool(existing_player.get("adopted", False)):
        message = (
            "You already have a horse. "
            "You can visit them with `/horse` and say hello with `/greet`."
        )
        return StartOnboardingResult(
            player=existing_player,
            message=message,
            already_adopted=True,
            reused_active_session=False,
            presentation=ResponsePresentation(
                title="Your Stable Is Waiting",
                description=message,
                fields=(
                    PresentationField(
                        name="Available Commands",
                        value="Use `/horse profile` to check in and `/greet` to visit your horse.",
                    ),
                ),
                accent="info",
            ),
        )

    if _has_active_onboarding(existing_player):
        if existing_player is None:
            raise RuntimeError("Unexpected missing player during active onboarding check.")
        message = (
            "Your adoption journey is already underway. "
            "Use `/horse view` to see your candidates."
        )
        return StartOnboardingResult(
            player=existing_player,
            message=message,
            already_adopted=False,
            reused_active_session=True,
            presentation=ResponsePresentation(
                title="Adoption In Progress",
                description=message,
                fields=(
                    PresentationField(
                        name="Next Step",
                        value="Open your candidate list with `/horse view`.",
                    ),
                ),
                accent="info",
            ),
        )

    candidates = candidate_generator(candidate_seed)
    started_player = repository.start_onboarding(
        user_id=user_id,
        guild_id=guild_id,
        candidates=candidates,
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="start_onboarding",
        user_id=user_id,
        guild_id=guild_id,
    )

    message = (
        "Welcome to Pferdehof. "
        "Three horses are waiting to meet you. Use `/horse view` to see your candidates."
    )
    return StartOnboardingResult(
        player=started_player,
        message=message,
        already_adopted=False,
        reused_active_session=False,
        presentation=ResponsePresentation(
            title="Welcome To Pferdehof",
            description="Three horses are waiting to meet you.",
            fields=(
                PresentationField(
                    name="Next Step",
                    value="Run `/horse view` and choose the horse that fits your style.",
                ),
            ),
            accent="success",
            footer="Your adoption journey has started.",
        ),
    )


def _has_active_onboarding(player: PlayerRecord | None) -> bool:
    if player is None:
        return False
    session = player.get("onboarding_session") or {}
    return bool(session.get("active", False))


def view_candidates_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    telemetry_logger: TelemetryLogger | None = None,
) -> ViewCandidatesResult:
    """Render onboarding candidates for a player with an active adoption session."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None:
        message = (
            "No adoption session is active yet. "
            "Use `/start` to begin your horse journey."
        )
        return ViewCandidatesResult(
            player=None,
            message=message,
            has_active_session=False,
            already_adopted=False,
            presentation=_build_presentation(
                title="No Active Adoption",
                description=message,
                accent="warning",
                fields=(
                    PresentationField(name="Next Step", value="Use `/start` to begin your horse journey."),
                ),
            ),
        )

    if bool(player.get("adopted", False)):
        message = (
            "You already adopted your horse. "
            "Visit them with `/horse` and say hello with `/greet`."
        )
        return ViewCandidatesResult(
            player=player,
            message=message,
            has_active_session=False,
            already_adopted=True,
            presentation=_build_presentation(
                title="Adoption Complete",
                description=message,
                accent="info",
            ),
        )

    session = player.get("onboarding_session") or {}
    if not bool(session.get("active", False)):
        message = (
            "No adoption session is active yet. "
            "Use `/start` to begin your horse journey."
        )
        return ViewCandidatesResult(
            player=player,
            message=message,
            has_active_session=False,
            already_adopted=False,
            presentation=_build_presentation(
                title="No Active Adoption",
                description=message,
                accent="warning",
                fields=(
                    PresentationField(name="Next Step", value="Use `/start` to begin your horse journey."),
                ),
            ),
        )

    candidates = session.get("candidates", [])
    if not candidates:
        message = (
            "Your adoption session has no candidates right now. "
            "Use `/start` to refresh your journey."
        )
        return ViewCandidatesResult(
            player=player,
            message=message,
            has_active_session=False,
            already_adopted=False,
            presentation=_build_presentation(
                title="Candidates Unavailable",
                description=message,
                accent="warning",
            ),
        )

    lines = [
        "Here are your horse candidates:",
        "",
    ]
    for candidate in candidates:
        candidate_id = str(candidate.get("id", "?")).upper()
        appearance = str(candidate.get("appearance_text", "Unknown appearance"))
        hint = str(candidate.get("hint", "Unknown hint"))
        lines.append(f"{candidate_id}: {appearance} | Hint: {hint}")

    lines.extend(
        [
            "",
            "Choose the one that feels right: `/horse choose <id>`",
        ]
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="viewed_candidates",
        user_id=user_id,
        guild_id=guild_id,
    )

    return ViewCandidatesResult(
        player=player,
        message="\n".join(lines),
        has_active_session=True,
        already_adopted=False,
        presentation=_build_presentation(
            title="Your Horse Candidates",
            description="Review your three candidates and pick the one that feels right.",
            accent="info",
            footer="Choose with `/horse choose <id>`",
            fields=tuple(
                PresentationField(
                    name=f"{str(candidate.get('id', '?')).upper()} Candidate",
                    value=(
                        f"{str(candidate.get('appearance_text', 'Unknown appearance'))}\n"
                        f"Hint: {str(candidate.get('hint', 'Unknown hint'))}"
                    ),
                )
                for candidate in candidates
            ),
        ),
    )


def choose_candidate_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    candidate_id: str,
    telemetry_logger: TelemetryLogger | None = None,
) -> ChooseCandidateResult:
    """Lock a candidate choice during onboarding and prompt naming."""
    normalized_candidate_id = candidate_id.strip().upper()
    valid_ids = {"A", "B", "C"}
    if normalized_candidate_id not in valid_ids:
        message = (
            "That candidate id is not valid. "
            "Please choose A, B, or C using `/horse choose <id>`."
        )
        return ChooseCandidateResult(
            player=None,
            message=message,
            selected_candidate_id=None,
            selection_locked=False,
            invalid_candidate_id=True,
            has_active_session=False,
            already_adopted=False,
            presentation=_build_presentation(
                title="Invalid Candidate",
                description=message,
                accent="warning",
            ),
        )

    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None:
        message = (
            "No adoption session is active yet. "
            "Use `/start` to begin your horse journey."
        )
        return ChooseCandidateResult(
            player=None,
            message=message,
            selected_candidate_id=None,
            selection_locked=False,
            invalid_candidate_id=False,
            has_active_session=False,
            already_adopted=False,
        )

    if bool(player.get("adopted", False)):
        message = (
            "You already adopted your horse. "
            "Visit them with `/horse` and say hello with `/greet`."
        )
        return ChooseCandidateResult(
            player=player,
            message=message,
            selected_candidate_id=None,
            selection_locked=False,
            invalid_candidate_id=False,
            has_active_session=False,
            already_adopted=True,
        )

    session = player.get("onboarding_session") or {}
    if not bool(session.get("active", False)):
        message = (
            "No adoption session is active yet. "
            "Use `/start` to begin your horse journey."
        )
        return ChooseCandidateResult(
            player=player,
            message=message,
            selected_candidate_id=None,
            selection_locked=False,
            invalid_candidate_id=False,
            has_active_session=False,
            already_adopted=False,
        )

    chosen_candidate_id = session.get("chosen_candidate_id")
    if chosen_candidate_id:
        message = (
            f"Your choice is already locked to {str(chosen_candidate_id).upper()}. "
            "In this MVP, choices are irreversible. Continue with `/horse name <name>`."
        )
        return ChooseCandidateResult(
            player=player,
            message=message,
            selected_candidate_id=str(chosen_candidate_id).upper(),
            selection_locked=True,
            invalid_candidate_id=False,
            has_active_session=True,
            already_adopted=False,
            presentation=_build_presentation(
                title="Choice Already Locked",
                description=message,
                accent="info",
            ),
        )

    candidates = session.get("candidates", [])
    candidate_ids = {str(candidate.get("id", "")).upper() for candidate in candidates}
    if normalized_candidate_id not in candidate_ids:
        message = (
            f"I could not find candidate {normalized_candidate_id}. "
            "Use `/horse view` to see your current A/B/C options."
        )
        return ChooseCandidateResult(
            player=player,
            message=message,
            selected_candidate_id=None,
            selection_locked=False,
            invalid_candidate_id=True,
            has_active_session=True,
            already_adopted=False,
            presentation=_build_presentation(
                title="Candidate Not Found",
                description=message,
                accent="warning",
            ),
        )

    updated_player = repository.set_chosen_candidate(
        user_id=user_id,
        guild_id=guild_id,
        candidate_id=normalized_candidate_id,
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="chose_candidate",
        user_id=user_id,
        guild_id=guild_id,
        candidate_id=normalized_candidate_id,
    )
    message = (
        f"Wonderful choice. Candidate {normalized_candidate_id} is now locked in. "
        "Give your horse a name with `/horse name <name>`."
    )
    return ChooseCandidateResult(
        player=updated_player,
        message=message,
        selected_candidate_id=normalized_candidate_id,
        selection_locked=True,
        invalid_candidate_id=False,
        has_active_session=True,
        already_adopted=False,
        presentation=_build_presentation(
            title="Candidate Locked In",
            description=message,
            accent="success",
            fields=(
                PresentationField(name="Next Step", value="Finalize adoption with `/horse name <name>`."),
            ),
        ),
    )


def name_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    horse_name: str,
    telemetry_logger: TelemetryLogger | None = None,
) -> NameHorseResult:
    """Finalize horse adoption by validating and persisting a horse name."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None:
        message = (
            "No adoption session is active yet. "
            "Use `/start` to begin your horse journey."
        )
        return NameHorseResult(
            player=None,
            message=message,
            finalized=False,
            invalid_name=False,
            has_active_session=False,
            has_chosen_candidate=False,
            already_adopted=False,
        )

    if bool(player.get("adopted", False)):
        message = (
            "You already adopted your horse. "
            "Visit them with `/horse` and say hello with `/greet`."
        )
        return NameHorseResult(
            player=player,
            message=message,
            finalized=False,
            invalid_name=False,
            has_active_session=False,
            has_chosen_candidate=False,
            already_adopted=True,
        )

    session = player.get("onboarding_session") or {}
    if not bool(session.get("active", False)):
        message = (
            "No adoption session is active yet. "
            "Use `/start` to begin your horse journey."
        )
        return NameHorseResult(
            player=player,
            message=message,
            finalized=False,
            invalid_name=False,
            has_active_session=False,
            has_chosen_candidate=False,
            already_adopted=False,
        )

    chosen_candidate_id = session.get("chosen_candidate_id")
    if not chosen_candidate_id:
        message = (
            "Choose your horse first. "
            "Use `/horse choose <id>` before naming your horse."
        )
        return NameHorseResult(
            player=player,
            message=message,
            finalized=False,
            invalid_name=False,
            has_active_session=True,
            has_chosen_candidate=False,
            already_adopted=False,
        )

    normalized_name, name_error = validate_horse_name(horse_name)
    if name_error == "length":
        message = (
            "That name needs to be between 2 and 20 characters. "
            "Try `/horse name <name>` with a shorter or longer name."
        )
        return NameHorseResult(
            player=player,
            message=message,
            finalized=False,
            invalid_name=True,
            has_active_session=True,
            has_chosen_candidate=True,
            already_adopted=False,
            presentation=_build_presentation(
                title="Name Needs Adjustment",
                description=message,
                accent="warning",
            ),
        )

    if name_error == "profanity":
        _logger.warning(
            "Blocked naming attempt by user_id=%s guild_id=%s name=%r.",
            user_id,
            guild_id,
            normalized_name,
        )
        message = (
            "That name cannot be used. "
            "Please choose a kinder name with `/horse name <name>`."
        )
        return NameHorseResult(
            player=player,
            message=message,
            finalized=False,
            invalid_name=True,
            has_active_session=True,
            has_chosen_candidate=True,
            already_adopted=False,
            presentation=_build_presentation(
                title="Name Not Allowed",
                description=message,
                accent="error",
            ),
        )

    updated_player = repository.finalize_horse_name(
        user_id=user_id,
        guild_id=guild_id,
        name=normalized_name,
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="named_horse",
        user_id=user_id,
        guild_id=guild_id,
        candidate_id=str(chosen_candidate_id),
    )
    horse = updated_player.get("horse") or {}
    appearance = str(horse.get("appearance", "a wonderful horse"))
    hint = _normalize_hint_text(horse.get("hint"), fallback="Steady-hearted and kind.")
    message = (
        f"What a beautiful name. {normalized_name} is officially your horse now. "
        f"Appearance: {appearance}. "
        f"First impression: {hint} "
        "Your adoption is complete."
    )
    return NameHorseResult(
        player=updated_player,
        message=message,
        finalized=True,
        invalid_name=False,
        has_active_session=False,
        has_chosen_candidate=True,
        already_adopted=False,
        presentation=_build_presentation(
            title=f"{normalized_name} Has Joined Your Stable",
            description="Your adoption is complete, and your horse is ready for their first day with you.",
            accent="success",
            fields=(
                PresentationField(name="Appearance", value=appearance),
                PresentationField(name="First Impression", value=hint),
                PresentationField(name="Try Next", value="Use `/horse profile` or say hello with `/greet`."),
            ),
        ),
    )


def admin_rename_horse_flow(
    repository: JsonPlayerRepository,
    admin_display_name: str,
    target_user_id: int,
    guild_id: int | None,
    new_name: str,
) -> AdminRenameHorseResult:
    """Override an adopted player's horse name (admin action).

    Permission enforcement (administrator check) is applied at the Discord
    command layer in ``CoreCog``.  This service function validates the new name
    and delegates persistence to the repository.
    """
    player = repository.get_player(user_id=target_user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            f"No adopted horse found for user {target_user_id}, {admin_display_name}. "
            "The player must have completed adoption before a rename is possible."
        )
        return AdminRenameHorseResult(
            player=player,
            message=message,
            renamed=False,
            invalid_name=False,
            target_has_horse=False,
        )

    normalized_name, name_error = validate_horse_name(new_name)
    if name_error is not None:
        if name_error == "length":
            reason = "between 2 and 20 characters"
        else:
            reason = "free of blocked terms"
        message = (
            f"The new name is not valid, {admin_display_name}. "
            f"Horse names must be {reason}."
        )
        return AdminRenameHorseResult(
            player=player,
            message=message,
            renamed=False,
            invalid_name=True,
            target_has_horse=True,
        )

    updated_player = repository.admin_rename_horse(
        user_id=target_user_id,
        guild_id=guild_id,
        new_name=normalized_name,
    )
    _logger.info(
        "Admin rename: admin=%r renamed horse for user_id=%s guild_id=%s new_name=%r.",
        admin_display_name,
        target_user_id,
        guild_id,
        normalized_name,
    )
    message = (
        f"Horse for user {target_user_id} has been renamed to {normalized_name}, "
        f"{admin_display_name}. Moderation action logged."
    )
    return AdminRenameHorseResult(
        player=updated_player,
        message=message,
        renamed=True,
        invalid_name=False,
        target_has_horse=True,
    )


def horse_profile_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
) -> HorseProfileResult:
    """Render the adopted horse profile or guide players into onboarding."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        onboarding_session = (player or {}).get("onboarding_session") or {}
        if bool(onboarding_session.get("active", False)):
            message = (
                "You have not adopted a horse yet. "
                "Use `/horse view` to review your candidates, or `/start` to restart onboarding."
            )
        else:
            message = (
                "You do not have a horse yet. "
                "Use `/start` to begin your adoption journey."
            )
        return HorseProfileResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            presentation=_build_presentation(
                title="No Adopted Horse Yet",
                description=message,
                accent="warning",
            ),
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    appearance = str(horse.get("appearance") or "a lovely companion")
    traits_visible_raw = horse.get("traits_visible")
    traits_visible = traits_visible_raw if isinstance(traits_visible_raw, list) else []
    visible_traits = [str(trait).strip() for trait in traits_visible if str(trait).strip()]
    trait_preview = visible_traits[:2]
    if not trait_preview:
        fallback_hint = str(horse.get("hint") or "steady-hearted")
        trait_preview = [fallback_hint]

    traits_text = ", ".join(trait_preview)
    state_presentation = build_horse_state_presentation(horse)
    lines = [
        "Here is your horse profile:",
        f"Name: {horse_name}",
        f"Appearance: {appearance}",
        f"Visible traits: {traits_text}",
        f"Mood: {horse_name} feels {state_presentation.readiness_feel}.",
        f"Bond ({state_presentation.bond_value}): {horse_name} is {state_presentation.bond_feel} with you.",
        f"Energy ({state_presentation.energy_value}): {horse_name} is {state_presentation.energy_feel}.",
        f"Health ({state_presentation.health_value}): {horse_name} is {state_presentation.health_feel}.",
        f"Confidence ({state_presentation.confidence_value}): {horse_name} is {state_presentation.confidence_feel}.",
        f"Skill ({state_presentation.skill_value}): {horse_name} is {state_presentation.skill_feel}.",
    ]

    if state_presentation.recent_activity_text is None:
        lines.append("Recent activity: Nothing recent yet - try a cozy interaction like `/greet`.")
    else:
        lines.append(f"Recent activity: {state_presentation.recent_activity_text}")

    return HorseProfileResult(
        player=player,
        message="\n".join(lines),
        has_adopted_horse=True,
        presentation=_build_presentation(
            title=f"{horse_name} - Horse Profile",
            description=f"{appearance}\nVisible traits: {traits_text}",
            accent="info",
            fields=tuple(
                PresentationField(name=f.name, value=f.value, inline=f.inline)
                for f in state_presentation.embed_fields
            ),
        ),
    )


def greet_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    telemetry_logger: TelemetryLogger | None = None,
) -> GreetHorseResult:
    """Render a lightweight personalized greeting for an adopted horse."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to greet yet. "
            "Start your adoption journey with `/start`."
        )
        return GreetHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
        )

    updated_player, is_first_interaction = repository.record_horse_interaction(
        user_id=user_id,
        guild_id=guild_id,
    )
    if is_first_interaction:
        _emit_telemetry(
            telemetry_logger=telemetry_logger,
            event_name="first_interaction",
            user_id=user_id,
            guild_id=guild_id,
        )

    horse = updated_player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    hint = _normalize_hint_text(horse.get("hint"), fallback="Gentle and attentive.")
    reaction = _greet_reaction_from_hint(horse_name=horse_name, hint=hint)
    message = (
        f"You greet {horse_name} softly. "
        f"{reaction} "
        f"First impression: {hint}"
    )
    return GreetHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        presentation=_build_presentation(
            title=f"You Greet {horse_name}",
            description=reaction,
            accent="success",
            fields=(
                PresentationField(name="First Impression", value=hint),
            ),
        ),
    )


def stable_roster_flow(
    repository: JsonPlayerRepository,
    guild_id: int | None,
    display_name: str,
    owner_display_name_resolver: Callable[[int], str | None] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
    user_id: int | None = None,
) -> StableRosterResult:
    """Render the adopted-horse roster for the current guild."""
    if guild_id is None:
        message = (
            "The stable roster needs a server stable to look at. "
            "Use `/stable` from a guild channel."
        )
        return StableRosterResult(
            rows=[],
            message=message,
            has_guild_context=False,
            is_empty=True,
            presentation=_build_presentation(
                title="Stable Unavailable",
                description=message,
                accent="warning",
            ),
        )

    raw_rows = repository.list_adopted_horses_by_guild(guild_id=guild_id)
    if not raw_rows:
        message = (
            "The stable is still quiet in this server. "
            "No horses have been adopted here yet. Use `/start` to welcome the first one."
        )
        return StableRosterResult(
            rows=[],
            message=message,
            has_guild_context=True,
            is_empty=True,
            presentation=_build_presentation(
                title="Stable Is Quiet",
                description=message,
                accent="info",
            ),
        )

    rows: list[dict[str, object]] = []
    lines = ["Here is the current stable roster:"]
    for raw_row in raw_rows:
        owner_user_id = int(raw_row["owner_user_id"])
        owner_display_name = _resolve_owner_display_name(
            owner_user_id=owner_user_id,
            owner_display_name_resolver=owner_display_name_resolver,
        )
        row = {
            "horse_id": int(raw_row["horse_id"]),
            "horse_name": str(raw_row["horse_name"]),
            "owner_user_id": owner_user_id,
            "owner_display_name": owner_display_name,
            "guild_id": guild_id,
        }
        rows.append(row)
        lines.append(
            f"#{row['horse_id']} | {row['horse_name']} | Owner: {row['owner_display_name']}"
        )

    lines.append("Use `/horse profile` to check on your own companion.")
    if user_id is not None:
        _emit_telemetry(
            telemetry_logger=telemetry_logger,
            event_name="viewed_stable",
            user_id=user_id,
            guild_id=guild_id,
        )
    return StableRosterResult(
        rows=rows,
        message="\n".join(lines),
        has_guild_context=True,
        is_empty=False,
        presentation=_build_presentation(
            title="Server Stable Roster",
            description="Here are the horses currently adopted in this server.",
            accent="info",
            fields=tuple(
                PresentationField(
                    name=f"#{row['horse_id']} - {row['horse_name']}",
                    value=f"Owner: {row['owner_display_name']}",
                )
                for row in rows
            ),
            footer="Use `/horse profile` to check on your own companion.",
        ),
    )


def _resolve_owner_display_name(
    owner_user_id: int,
    owner_display_name_resolver: Callable[[int], str | None] | None,
) -> str:
    if owner_display_name_resolver is None:
        return f"Unknown rider ({owner_user_id})"

    owner_display_name = owner_display_name_resolver(owner_user_id)
    if owner_display_name is None:
        return f"Unknown rider ({owner_user_id})"

    normalized_name = str(owner_display_name).strip()
    if not normalized_name:
        return f"Unknown rider ({owner_user_id})"

    return normalized_name


def _normalize_hint_text(value: object, fallback: str) -> str:
    hint_text = str(value).strip() if value is not None else ""
    if not hint_text:
        hint_text = fallback.strip()

    if hint_text[-1] not in {".", "!", "?"}:
        hint_text = f"{hint_text}."
    return hint_text


def _greet_reaction_from_hint(horse_name: str, hint: str) -> str:
    lowered_hint = hint.lower()
    if "calm" in lowered_hint or "composed" in lowered_hint or "steady" in lowered_hint:
        return f"{horse_name} stays relaxed, steps closer, and seems happy to see you."
    if "lively" in lowered_hint or "eager" in lowered_hint or "spark" in lowered_hint:
        return f"{horse_name} pricks their ears, steps in eagerly, and seems happy to see you."
    if "connect" in lowered_hint or "leans" in lowered_hint or "trust" in lowered_hint:
        return f"{horse_name} leans in toward you and seems happy to see you."
    if "learn" in lowered_hint or "routines" in lowered_hint or "closely" in lowered_hint:
        return f"{horse_name} watches you closely, steps closer, and seems happy to see you."
    return f"{horse_name} steps closer and seems happy to see you."
