"""Onboarding flow services for horse adoption journey commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import random
from typing import Callable, Sequence

_logger = logging.getLogger(__name__)

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.repositories.player_repository import CandidateRecord, PlayerRecord

from .candidate_generator import generate_candidate_horses
from .moderation import contains_blocked_name_term, validate_horse_name
from .ride_outcomes import RideOutcomeResult, select_ride_outcome
from .state_presentation import build_horse_state_presentation
from .telemetry import TelemetryEventName, TelemetryLogger


_RIDE_GENERIC_OPENING_POOL: tuple[str, ...] = (
    "The path opens up gently, and the two of you settle into an easy rhythm.",
    "The ride begins with quiet focus, with hoofbeats and breath finding the same cadence.",
    "A calm stretch of trail gives you both space to settle and listen to each other.",
)

_RIDE_GENERIC_CLOSING_POOL: tuple[str, ...] = (
    "Back at the stable, the ride lingers as one of those moments that quietly matter.",
    "By the time you head home, both of you feel a little more in tune than before.",
    "When you turn for home, it feels like another small chapter in your shared story.",
)

_RIDE_ENERGY_NARRATIVE_BY_TIER: dict[str, tuple[str, ...]] = {
    "low": (
        "Even after the outing, {horse_name} is only lightly winded and still moving with ease.",
        "The effort leaves {horse_name} lightly winded, with plenty of spark still in the stride.",
    ),
    "medium": (
        "The work leaves {horse_name} noticeably tired, and the slower walk home feels well earned.",
        "By the end, {horse_name} is noticeably tired and grateful for the gentler pace back.",
    ),
    "high": (
        "That stretch pushes hard, and {horse_name} comes back deeply spent after giving so much.",
        "It is a demanding effort, and {horse_name} returns deeply spent but still willing.",
    ),
}

_RIDE_HEALTH_LOSS_NARRATIVE_BY_TIER: dict[str, tuple[str, ...]] = {
    "low": (
        "A small mishap on uneven ground causes a minor scrape before you steady things quickly.",
        "There is a small mishap over rough footing, leaving a minor scrape before you ease off.",
    ),
    "medium": (
        "A small mishap on the trail knocks the rhythm off for a moment and leaves clear soreness.",
        "One small mishap near a bend leads to a clumsy step and a bit more soreness than expected.",
    ),
    "high": (
        "A small mishap late in the ride turns into a heavier jolt, so you finish carefully and head home.",
        "Near the end, a small mishap causes a hard stumble, and you call the tougher work there.",
    ),
}

_RIDE_HEALTH_STEADY_POOL: tuple[str, ...] = (
    "Across the whole route, {horse_name} stays sure-footed and comfortable.",
    "No rough moment takes hold today; {horse_name} stays sure-footed from start to finish.",
)

_RIDE_STAT_GAIN_NARRATIVE_BY_TIER: dict[str, tuple[str, ...]] = {
    "low": (
        "You notice a little breakthrough in {stat_name} by the time you finish.",
        "By the end, there is a little breakthrough in {stat_name} worth building on.",
    ),
    "medium": (
        "The session lands as a solid breakthrough in {stat_name}.",
        "You can feel a solid breakthrough in {stat_name} settling in.",
    ),
    "high": (
        "Somewhere mid-ride, a major breakthrough in {stat_name} clicks into place.",
        "It turns into a major breakthrough in {stat_name} that you both seem to feel.",
    ),
}

_RIDE_STAT_NO_GAIN_POOL: tuple[str, ...] = (
    "There is no obvious jump in {stat_name} today, but the steady practice still counts.",
    "{stat_name_cap} stays about the same this time, yet the consistency will matter later.",
)


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
class FeedHorseResult:
    """Result payload for `/feed` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    energy_gain: int
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class GroomHorseResult:
    """Result payload for `/groom` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    groomed_stat: str | None
    stat_gain: int
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class RestHorseResult:
    """Result payload for `/rest` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    health_gain: int
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class TrainHorseResult:
    """Result payload for `/train` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    blocked_by_readiness: bool
    skill_gain: int
    confidence_gain: int
    energy_cost: int
    health_loss: int
    presentation: ResponsePresentation | None = None


@dataclass(frozen=True)
class RideHorseResult:
    """Result payload for `/ride` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool
    blocked_by_readiness: bool
    outcome: RideOutcomeResult | None
    ride_stat: str | None
    """The stat subject to the chance-to-increase check: 'confidence' or 'bond'."""
    ride_stat_gain: int
    energy_loss: int
    health_loss: int
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
        f"Bond: {horse_name} is {state_presentation.bond_feel} with you.",
        f"Energy: {horse_name} is {state_presentation.energy_feel}.",
        f"Confidence: {horse_name} is {state_presentation.confidence_feel}.",
        f"Skill: {horse_name} is {state_presentation.skill_feel}.",
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


def feed_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    d10_roll: Callable[[], int] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> FeedHorseResult:
    """Feed an adopted horse to restore energy and persist recent activity."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to feed yet. "
            "Start your adoption journey with `/start`."
        )
        return FeedHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            energy_gain=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    current_energy = int(horse.get("energy") or 0)
    roll = d10_roll() if d10_roll is not None else _roll_d10()
    energy_gain = _clamp_stat(roll, minimum=1, maximum=10)
    updated_energy = _clamp_stat(current_energy + energy_gain)
    recent_activity = (
        f"You fed {horse_name}, and {horse_name} perked up right away (+{energy_gain} energy)."
    )

    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates={
            "energy": updated_energy,
            "last_fed_at": _timestamp_now(),
            "recent_activity": recent_activity,
        },
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="fed_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )

    message = (
        f"You offer a warm feed to {horse_name}. "
        f"{horse_name} munches happily and feels brighter (+{energy_gain} energy)."
    )
    return FeedHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        energy_gain=energy_gain,
        presentation=_build_presentation(
            title=f"{horse_name} Enjoyed The Feed",
            description=message,
            accent="success",
            fields=(
                PresentationField(name="Energy Gained", value=f"+{energy_gain}"),
            ),
        ),
    )


def groom_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    stat_selector: Callable[[], str] | None = None,
    d100_roll: Callable[[], int] | None = None,
    d10_roll: Callable[[], int] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> GroomHorseResult:
    """Groom an adopted horse with a chance to increase bond or health."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to groom yet. "
            "Start your adoption journey with `/start`."
        )
        return GroomHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            groomed_stat=None,
            stat_gain=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    selected_stat = stat_selector() if stat_selector is not None else random.choice(("bond", "health"))
    if selected_stat not in {"bond", "health"}:
        selected_stat = "bond"

    current_value = _clamp_stat(int(horse.get(selected_stat) or 0))
    check_roll = _clamp_stat((d100_roll() if d100_roll is not None else _roll_d100()), minimum=1)

    stat_gain = 0
    if check_roll > current_value:
        rolled_gain = d10_roll() if d10_roll is not None else _roll_d10()
        stat_gain = _clamp_stat(rolled_gain, minimum=1, maximum=10)

    updated_value = _clamp_stat(current_value + stat_gain)
    stat_label = "bond" if selected_stat == "bond" else "health"

    if stat_gain > 0:
        reaction_text = (
            f"{horse_name} melts into the brushing and seems noticeably calmer (+{stat_gain} {stat_label})."
        )
    else:
        reaction_text = (
            f"{horse_name} relaxes into the grooming routine. It is a quiet, comforting moment today."
        )

    recent_activity = f"You groomed {horse_name}. {reaction_text}"
    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates={
            selected_stat: updated_value,
            "last_groomed_at": _timestamp_now(),
            "recent_activity": recent_activity,
        },
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="groomed_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )

    message = f"You groom {horse_name} carefully. {reaction_text}"
    return GroomHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        groomed_stat=selected_stat,
        stat_gain=stat_gain,
        presentation=_build_presentation(
            title=f"{horse_name} Is Groomed",
            description=message,
            accent="success",
            fields=(
                PresentationField(name="Stat Focus", value=stat_label.capitalize(), inline=True),
                PresentationField(name="Gain", value=f"+{stat_gain}" if stat_gain > 0 else "No increase", inline=True),
            ),
        ),
    )


def rest_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    d10_roll: Callable[[], int] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> RestHorseResult:
    """Rest an adopted horse to restore health and persist recent activity."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to rest yet. "
            "Start your adoption journey with `/start`."
        )
        return RestHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            health_gain=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    current_health = int(horse.get("health") or 0)
    roll = d10_roll() if d10_roll is not None else _roll_d10()
    health_gain = _clamp_stat(roll, minimum=1, maximum=10)
    updated_health = _clamp_stat(current_health + health_gain)
    recent_activity = (
        f"{horse_name} rested quietly in the stable and feels healthier (+{health_gain} health)."
    )

    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates={
            "health": updated_health,
            "last_rested_at": _timestamp_now(),
            "recent_activity": recent_activity,
        },
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="rested_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )

    message = (
        f"You settle {horse_name} in for a comfortable rest. "
        f"{horse_name} dozes peacefully and wakes up feeling better (+{health_gain} health)."
    )
    return RestHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        health_gain=health_gain,
        presentation=_build_presentation(
            title=f"{horse_name} Had A Rest",
            description=message,
            accent="success",
            fields=(
                PresentationField(name="Health Gained", value=f"+{health_gain}"),
            ),
        ),
    )


def train_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    d100_roll: Callable[[], int] | None = None,
    d10_roll: Callable[[], int] | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> TrainHorseResult:
    """Train an adopted horse with readable progression, risk, and energy tradeoffs."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to train yet. "
            "Start your adoption journey with `/start`."
        )
        return TrainHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            blocked_by_readiness=False,
            skill_gain=0,
            confidence_gain=0,
            energy_cost=0,
            health_loss=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    current_energy = _clamp_stat(int(horse.get("energy") or 0))
    current_health = _clamp_stat(int(horse.get("health") or 0))
    current_skill = _clamp_stat(int(horse.get("skill") or 0))
    current_confidence = _clamp_stat(int(horse.get("confidence") or 0))

    if current_energy < 30 or current_health < 35:
        state_presentation = build_horse_state_presentation(horse)
        recovery_guidance = "Try `/feed` or `/rest` first, then come back to `/train`."
        message = (
            f"You hold off on training {horse_name} for now. "
            f"{horse_name} feels {state_presentation.readiness_feel}. "
            f"Recovery Tip: {recovery_guidance}"
        )
        return TrainHorseResult(
            player=player,
            message=message,
            has_adopted_horse=True,
            blocked_by_readiness=True,
            skill_gain=0,
            confidence_gain=0,
            energy_cost=0,
            health_loss=0,
            presentation=_build_presentation(
                title="Training Deferred",
                description=(
                    f"You hold off on training {horse_name} for now. "
                    f"{horse_name} feels {state_presentation.readiness_feel}."
                ),
                accent="warning",
                fields=(
                    PresentationField(name="Recovery Tip", value=recovery_guidance),
                ),
            ),
        )

    skill_gain = _chance_to_increase(
        current_value=current_skill,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )
    confidence_gain = _chance_to_increase(
        current_value=current_confidence,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )
    energy_cost_roll = d10_roll() if d10_roll is not None else _roll_d10()
    energy_cost = _clamp_stat(energy_cost_roll, minimum=1, maximum=10)
    health_loss = _slight_chance_to_decrease(
        checked_value=current_skill,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )

    updated_skill = _clamp_stat(current_skill + skill_gain)
    updated_confidence = _clamp_stat(current_confidence + confidence_gain)
    updated_energy = _clamp_stat(current_energy - energy_cost)
    updated_health = _clamp_stat(current_health - health_loss)

    recent_activity_parts = [f"You trained {horse_name}"]
    if skill_gain > 0:
        recent_activity_parts.append(f"{horse_name} picked up the lesson well (+{skill_gain} skill)")
    else:
        recent_activity_parts.append(f"{horse_name} stayed patient through a gentle practice")

    if confidence_gain > 0:
        recent_activity_parts.append(f"and warmed to the work (+{confidence_gain} confidence)")

    recent_activity_parts.append(f"while using up some energy (-{energy_cost} energy)")

    if health_loss > 0:
        recent_activity_parts.append(f"and came away a little sore (-{health_loss} health)")

    recent_activity = ". ".join(recent_activity_parts) + "."

    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates={
            "skill": updated_skill,
            "confidence": updated_confidence,
            "energy": updated_energy,
            "health": updated_health,
            "last_trained_at": _timestamp_now(),
            "recent_activity": recent_activity,
        },
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="trained_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )

    updated_horse = updated_player.get("horse") or {}
    state_presentation = build_horse_state_presentation(updated_horse)
    result_parts = []
    if skill_gain > 0:
        result_parts.append(f"+{skill_gain} skill")
    if confidence_gain > 0:
        result_parts.append(f"+{confidence_gain} confidence")
    result_parts.append(f"-{energy_cost} energy")
    if health_loss > 0:
        result_parts.append(f"-{health_loss} health")
    result_summary = ", ".join(result_parts)

    message = (
        f"You guide {horse_name} through a focused training session. "
        f"{horse_name} comes away {state_presentation.skill_feel} and {state_presentation.confidence_feel} ({result_summary}). "
        f"If {horse_name} still feels ready later, `/ride` is the next natural step."
    )
    return TrainHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        blocked_by_readiness=False,
        skill_gain=skill_gain,
        confidence_gain=confidence_gain,
        energy_cost=energy_cost,
        health_loss=health_loss,
        presentation=_build_presentation(
            title=f"Training Session With {horse_name}",
            description=(
                f"{horse_name} now feels {state_presentation.skill_feel} and "
                f"{state_presentation.confidence_feel}."
            ),
            accent="success",
            fields=(
                PresentationField(name="Skill", value=f"+{skill_gain}" if skill_gain > 0 else "No increase", inline=True),
                PresentationField(
                    name="Confidence",
                    value=f"+{confidence_gain}" if confidence_gain > 0 else "No increase",
                    inline=True,
                ),
                PresentationField(name="Energy", value=f"-{energy_cost}", inline=True),
                PresentationField(name="Health", value=f"-{health_loss}" if health_loss > 0 else "No loss", inline=True),
                PresentationField(name="Next Step", value=f"If {horse_name} feels ready, try `/ride`."),
            ),
        ),
    )


def ride_horse_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    stat_selector: Callable[[], str] | None = None,
    d100_roll: Callable[[], int] | None = None,
    d10_roll: Callable[[], int] | None = None,
    rng: random.Random | None = None,
    telemetry_logger: TelemetryLogger | None = None,
) -> RideHorseResult:
    """Take an adopted horse on a ride and persist the outcome as recent activity."""
    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None or not bool(player.get("adopted", False)):
        message = (
            "There is no horse to ride yet. "
            "Start your adoption journey with `/start`."
        )
        return RideHorseResult(
            player=player,
            message=message,
            has_adopted_horse=False,
            blocked_by_readiness=False,
            outcome=None,
            ride_stat=None,
            ride_stat_gain=0,
            energy_loss=0,
            health_loss=0,
        )

    horse = player.get("horse") or {}
    horse_name = str(horse.get("name") or "Your horse")
    current_energy = _clamp_stat(int(horse.get("energy") or 0))
    current_health = _clamp_stat(int(horse.get("health") or 0))
    current_skill = _clamp_stat(int(horse.get("skill") or 0))
    current_confidence = _clamp_stat(int(horse.get("confidence") or 0))
    current_bond = _clamp_stat(int(horse.get("bond") or 0))

    # Option A safety rule: require enough stats to cover maximum possible ride losses.
    # - Energy can decrease by up to 30 (3d10), so require at least 30.
    # - Health can decrease by up to 10 (1d10), so require at least 10.
    if current_energy < 30 or current_health < 10:
        state_presentation = build_horse_state_presentation(horse)
        recovery_guidance = "Try `/feed` or `/rest` first, then come back to `/ride`."
        message = (
            f"You decide not to ride {horse_name} right now. "
            f"{horse_name} feels {state_presentation.readiness_feel}. "
            f"Recovery Tip: {recovery_guidance}"
        )
        return RideHorseResult(
            player=player,
            message=message,
            has_adopted_horse=True,
            blocked_by_readiness=True,
            outcome=None,
            ride_stat=None,
            ride_stat_gain=0,
            energy_loss=0,
            health_loss=0,
            presentation=_build_presentation(
                title="Ride Deferred",
                description=(
                    f"You decide not to ride {horse_name} right now. "
                    f"{horse_name} feels {state_presentation.readiness_feel}."
                ),
                accent="warning",
                fields=(
                    PresentationField(name="Recovery Tip", value=recovery_guidance),
                ),
            ),
        )

    # Select the stat to try and increase (confidence or bond).
    selected_stat = stat_selector() if stat_selector is not None else random.choice(("confidence", "bond"))
    if selected_stat not in {"confidence", "bond"}:
        selected_stat = "confidence"
    current_selected_value = current_confidence if selected_stat == "confidence" else current_bond

    # Use the ride outcome engine to generate story text.
    outcome = select_ride_outcome(
        horse_name=horse_name,
        energy=current_energy,
        confidence=current_confidence,
        bond=current_bond,
        skill=current_skill,
        rng=rng,
    )

    # Chance to increase selected stat (confidence or bond) via 1d100 check.
    ride_stat_gain = _chance_to_increase(
        current_value=current_selected_value,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )

    # Energy always decreases by 3d10 (min 0).
    roll_1 = d10_roll() if d10_roll is not None else _roll_d10()
    roll_2 = d10_roll() if d10_roll is not None else _roll_d10()
    roll_3 = d10_roll() if d10_roll is not None else _roll_d10()
    energy_loss = _clamp_stat(roll_1 + roll_2 + roll_3, minimum=3, maximum=30)

    # Chance (skill check) to decrease health via 1d100 vs skill.
    health_loss = _chance_to_decrease(
        checked_value=current_skill,
        d100_roll=d100_roll,
        d10_roll=d10_roll,
    )

    updated_selected = _clamp_stat(current_selected_value + ride_stat_gain)
    updated_energy = _clamp_stat(current_energy - energy_loss)
    updated_health = _clamp_stat(current_health - health_loss)

    _rng = rng if rng is not None else random.Random()
    contextual_story, contextual_recent = _compose_ride_roll_narrative(
        horse_name=horse_name,
        ride_stat=selected_stat,
        ride_stat_gain=ride_stat_gain,
        energy_loss=energy_loss,
        health_loss=health_loss,
        rng=_rng,
    )

    recent_activity = f"{outcome.recent_activity_text} {contextual_recent}"
    updates: dict[str, object] = {
        selected_stat: updated_selected,
        "energy": updated_energy,
        "health": updated_health,
        "last_rode_at": _timestamp_now(),
        "recent_activity": recent_activity,
    }
    updated_player = repository.update_horse_state(
        user_id=user_id,
        guild_id=guild_id,
        updates=updates,
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="rode_horse",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
    )
    _emit_telemetry(
        telemetry_logger=telemetry_logger,
        event_name="ride_outcome",
        user_id=user_id,
        guild_id=guild_id,
        horse_name=horse_name,
        outcome_id=outcome.outcome_id,
        outcome_category=outcome.category,
    )

    result_parts: list[str] = []
    if ride_stat_gain > 0:
        result_parts.append(f"+{ride_stat_gain} {selected_stat}")
    result_parts.append(f"-{energy_loss} energy")
    if health_loss > 0:
        result_parts.append(f"-{health_loss} health")
    result_summary = ", ".join(result_parts)

    message = (
        f"{outcome.story_text}\n\n"
        f"{contextual_story}\n\n"
        f"({result_summary})\n\nUse `/horse profile` to see {horse_name}'s updated profile."
    )
    return RideHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
        blocked_by_readiness=False,
        outcome=outcome,
        ride_stat=selected_stat,
        ride_stat_gain=ride_stat_gain,
        energy_loss=energy_loss,
        health_loss=health_loss,
        presentation=_build_presentation(
            title="Ride Complete",
            description=outcome.story_text,
            accent=outcome.accent,
            fields=(
                PresentationField(name="Ride Notes", value=contextual_story),
                PresentationField(
                    name="Result",
                    value=(
                        f"{selected_stat.capitalize()}: +{ride_stat_gain}\n"
                        f"Energy: -{energy_loss}\n"
                        + (f"Health: -{health_loss}" if health_loss > 0 else "Health: no loss")
                    ),
                    inline=True,
                ),
                PresentationField(name="Next Step", value=f"Use `/horse profile` to check {horse_name}'s updated state."),
            ),
            footer=f"Outcome: {outcome.category}",
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


def _emit_telemetry(
    telemetry_logger: TelemetryLogger | None,
    event_name: TelemetryEventName,
    user_id: int,
    guild_id: int | None,
    candidate_id: str | None = None,
    horse_name: str | None = None,
    outcome_id: str | None = None,
    outcome_category: str | None = None,
) -> None:
    if telemetry_logger is None:
        return
    telemetry_logger.emit(
        event_name=event_name,
        user_id=user_id,
        guild_id=guild_id,
        candidate_id=candidate_id,
        horse_name=horse_name,
        outcome_id=outcome_id,
        outcome_category=outcome_category,
    )


def _roll_d10() -> int:
    """Return a uniform d10 roll for state deltas."""
    return random.randint(1, 10)


def _roll_d100() -> int:
    """Return a uniform d100 roll for chance-based checks."""
    return random.randint(1, 100)


def _chance_to_increase(
    current_value: int,
    d100_roll: Callable[[], int] | None,
    d10_roll: Callable[[], int] | None,
) -> int:
    check_roll = _clamp_stat((d100_roll() if d100_roll is not None else _roll_d100()), minimum=1)
    if check_roll <= current_value:
        return 0

    rolled_gain = d10_roll() if d10_roll is not None else _roll_d10()
    return _clamp_stat(rolled_gain, minimum=1, maximum=10)


def _chance_to_decrease(
    checked_value: int,
    d100_roll: Callable[[], int] | None,
    d10_roll: Callable[[], int] | None,
) -> int:
    """Roll 1d100 against checked_value; if roll exceeds it, return a 1d10 loss amount."""
    check_roll = _clamp_stat((d100_roll() if d100_roll is not None else _roll_d100()), minimum=1)
    if check_roll <= checked_value:
        return 0
    rolled_loss = d10_roll() if d10_roll is not None else _roll_d10()
    return _clamp_stat(rolled_loss, minimum=1, maximum=10)


def _slight_chance_to_decrease(
    checked_value: int,
    d100_roll: Callable[[], int] | None,
    d10_roll: Callable[[], int] | None,
) -> int:
    first_roll = _clamp_stat((d100_roll() if d100_roll is not None else _roll_d100()), minimum=1)
    second_roll = _clamp_stat((d100_roll() if d100_roll is not None else _roll_d100()), minimum=1)
    if first_roll <= checked_value or second_roll <= checked_value:
        return 0

    rolled_loss = d10_roll() if d10_roll is not None else _roll_d10()
    return _clamp_stat(rolled_loss, minimum=1, maximum=10)


def _compose_ride_roll_narrative(
    horse_name: str,
    ride_stat: str,
    ride_stat_gain: int,
    energy_loss: int,
    health_loss: int,
    rng: random.Random,
) -> tuple[str, str]:
    """Build descriptive ride text from roll outcomes with future-stat compatibility."""
    stat_name = ride_stat.replace("_", " ").strip() or "readiness"
    stat_name_cap = stat_name.capitalize()

    energy_tier = _delta_tier(amount=energy_loss, max_amount=30)
    health_tier = _delta_tier(amount=health_loss, max_amount=10)
    gain_tier = _delta_tier(amount=ride_stat_gain, max_amount=10)

    parts: list[str] = [_pick(pool=_RIDE_GENERIC_OPENING_POOL, rng=rng)]
    parts.append(
        _pick(pool=_RIDE_ENERGY_NARRATIVE_BY_TIER[energy_tier], rng=rng).format(horse_name=horse_name)
    )

    if health_loss > 0:
        parts.append(
            _pick(pool=_RIDE_HEALTH_LOSS_NARRATIVE_BY_TIER[health_tier], rng=rng).format(
                horse_name=horse_name
            )
        )
    else:
        parts.append(_pick(pool=_RIDE_HEALTH_STEADY_POOL, rng=rng).format(horse_name=horse_name))

    if ride_stat_gain > 0:
        parts.append(
            _pick(pool=_RIDE_STAT_GAIN_NARRATIVE_BY_TIER[gain_tier], rng=rng).format(
                stat_name=stat_name,
                stat_name_cap=stat_name_cap,
            )
        )
    else:
        parts.append(
            _pick(pool=_RIDE_STAT_NO_GAIN_POOL, rng=rng).format(
                stat_name=stat_name,
                stat_name_cap=stat_name_cap,
            )
        )

    parts.append(_pick(pool=_RIDE_GENERIC_CLOSING_POOL, rng=rng))

    story_text = " ".join(parts)
    recent_text = (
        f"Ride notes: {_build_recent_energy_fragment(horse_name=horse_name, energy_tier=energy_tier)} "
        f"{_build_recent_health_fragment(health_loss=health_loss)} "
        f"{_build_recent_stat_fragment(stat_name=stat_name, ride_stat_gain=ride_stat_gain)}"
    )
    return story_text, recent_text


def _build_recent_energy_fragment(horse_name: str, energy_tier: str) -> str:
    if energy_tier == "low":
        return f"{horse_name} is lightly winded."
    if energy_tier == "medium":
        return f"{horse_name} is noticeably tired."
    return f"{horse_name} is deeply spent."


def _build_recent_health_fragment(health_loss: int) -> str:
    if health_loss > 0:
        return "A small mishap left some soreness."
    return "No rough moment caused health trouble."


def _build_recent_stat_fragment(stat_name: str, ride_stat_gain: int) -> str:
    if ride_stat_gain > 0:
        return f"{stat_name.capitalize()} saw a breakthrough (+{ride_stat_gain})."
    return f"{stat_name.capitalize()} held steady this ride."


def _delta_tier(amount: int, max_amount: int) -> str:
    """Map a positive delta amount to low/medium/high narrative tiers."""
    normalized = max(0, min(max_amount, int(amount)))
    if normalized <= 0:
        return "low"
    if normalized <= max_amount // 3:
        return "low"
    if normalized <= (2 * max_amount) // 3:
        return "medium"
    return "high"


def _pick(pool: Sequence[str], rng: random.Random) -> str:
    return rng.choice(tuple(pool))


def _clamp_stat(value: int, minimum: int = 0, maximum: int = 100) -> int:
    """Clamp a horse state value within configured bounds."""
    return max(minimum, min(maximum, int(value)))


def _timestamp_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(tz=UTC).isoformat()


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
