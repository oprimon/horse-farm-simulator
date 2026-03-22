"""Onboarding flow services for horse adoption journey commands."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable

_logger = logging.getLogger(__name__)

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.repositories.player_repository import CandidateRecord, PlayerRecord

from .candidate_generator import generate_candidate_horses
from .moderation import contains_blocked_name_term, validate_horse_name
from .telemetry import TelemetryLogger


@dataclass(frozen=True)
class StartOnboardingResult:
    """Result payload for `/start` onboarding flow execution."""

    player: PlayerRecord
    message: str
    already_adopted: bool
    reused_active_session: bool


@dataclass(frozen=True)
class ViewCandidatesResult:
    """Result payload for `/horse view` command execution."""

    player: PlayerRecord | None
    message: str
    has_active_session: bool
    already_adopted: bool


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


@dataclass(frozen=True)
class HorseProfileResult:
    """Result payload for `/horse` profile command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool


@dataclass(frozen=True)
class GreetHorseResult:
    """Result payload for `/greet` command execution."""

    player: PlayerRecord | None
    message: str
    has_adopted_horse: bool


@dataclass(frozen=True)
class AdminRenameHorseResult:
    """Result payload for admin `horse rename` override command."""

    player: PlayerRecord | None
    message: str
    renamed: bool
    invalid_name: bool
    target_has_horse: bool


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
            f"You already have a horse, {display_name}. "
            "You can visit them with `/horse` and say hello with `/greet`."
        )
        return StartOnboardingResult(
            player=existing_player,
            message=message,
            already_adopted=True,
            reused_active_session=False,
        )

    if _has_active_onboarding(existing_player):
        if existing_player is None:
            raise RuntimeError("Unexpected missing player during active onboarding check.")
        message = (
            f"Your adoption journey is already underway, {display_name}. "
            "Use `/horse view` to see your candidates."
        )
        return StartOnboardingResult(
            player=existing_player,
            message=message,
            already_adopted=False,
            reused_active_session=True,
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
        f"Welcome to Pferdehof, {display_name}. "
        "Three horses are waiting to meet you. Use `/horse view` to see your candidates."
    )
    return StartOnboardingResult(
        player=started_player,
        message=message,
        already_adopted=False,
        reused_active_session=False,
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
            f"No adoption session is active yet, {display_name}. "
            "Use `/start` to begin your horse journey."
        )
        return ViewCandidatesResult(
            player=None,
            message=message,
            has_active_session=False,
            already_adopted=False,
        )

    if bool(player.get("adopted", False)):
        message = (
            f"You already adopted your horse, {display_name}. "
            "Visit them with `/horse` and say hello with `/greet`."
        )
        return ViewCandidatesResult(
            player=player,
            message=message,
            has_active_session=False,
            already_adopted=True,
        )

    session = player.get("onboarding_session") or {}
    if not bool(session.get("active", False)):
        message = (
            f"No adoption session is active yet, {display_name}. "
            "Use `/start` to begin your horse journey."
        )
        return ViewCandidatesResult(
            player=player,
            message=message,
            has_active_session=False,
            already_adopted=False,
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
        )

    lines = [
        f"Here are your horse candidates, {display_name}:",
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
            f"That candidate id is not valid, {display_name}. "
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
        )

    player = repository.get_player(user_id=user_id, guild_id=guild_id)
    if player is None:
        message = (
            f"No adoption session is active yet, {display_name}. "
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
            f"You already adopted your horse, {display_name}. "
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
            f"No adoption session is active yet, {display_name}. "
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
            f"Your choice is already locked to {str(chosen_candidate_id).upper()}, {display_name}. "
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
        )

    candidates = session.get("candidates", [])
    candidate_ids = {str(candidate.get("id", "")).upper() for candidate in candidates}
    if normalized_candidate_id not in candidate_ids:
        message = (
            f"I could not find candidate {normalized_candidate_id}, {display_name}. "
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
        f"Wonderful choice, {display_name}. Candidate {normalized_candidate_id} is now locked in. "
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
            f"No adoption session is active yet, {display_name}. "
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
            f"You already adopted your horse, {display_name}. "
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
            f"No adoption session is active yet, {display_name}. "
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
            f"Choose your horse first, {display_name}. "
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
            f"That name needs to be between 2 and 20 characters, {display_name}. "
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
        )

    if name_error == "profanity":
        _logger.warning(
            "Blocked naming attempt by user_id=%s guild_id=%s name=%r.",
            user_id,
            guild_id,
            normalized_name,
        )
        message = (
            f"That name cannot be used, {display_name}. "
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
    hint = str(horse.get("hint", "steady-hearted"))
    message = (
        f"What a beautiful name, {display_name}. {normalized_name} is officially your horse now. "
        f"{normalized_name} appears as {appearance} and feels {hint}. "
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
                f"You have not adopted a horse yet, {display_name}. "
                "Use `/horse view` to review your candidates, or `/start` to restart onboarding."
            )
        else:
            message = (
                f"You do not have a horse yet, {display_name}. "
                "Use `/start` to begin your adoption journey."
            )
        return HorseProfileResult(
            player=player,
            message=message,
            has_adopted_horse=False,
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
    lines = [
        f"Here is your horse profile, {display_name}:",
        f"Name: {horse_name}",
        f"Appearance: {appearance}",
        f"Visible traits: {traits_text}",
        f"Mood: {horse_name} seems calm and close to you today.",
        f"Energy: {horse_name} is ready for a gentle ride and a warm greeting.",
    ]

    return HorseProfileResult(
        player=player,
        message="\n".join(lines),
        has_adopted_horse=True,
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
            f"There is no horse to greet yet, {display_name}. "
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
    hint = str(horse.get("hint") or "gentle")
    message = (
        f"You greet {horse_name} softly, {display_name}. "
        f"{horse_name} steps closer with a {hint.lower()} spark and seems happy to see you."
    )
    return GreetHorseResult(
        player=updated_player,
        message=message,
        has_adopted_horse=True,
    )


def _emit_telemetry(
    telemetry_logger: TelemetryLogger | None,
    event_name: str,
    user_id: int,
    guild_id: int | None,
    candidate_id: str | None = None,
) -> None:
    if telemetry_logger is None:
        return
    telemetry_logger.emit(
        event_name=event_name,
        user_id=user_id,
        guild_id=guild_id,
        candidate_id=candidate_id,
    )
