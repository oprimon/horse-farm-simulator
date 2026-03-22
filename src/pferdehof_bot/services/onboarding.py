"""Onboarding flow services for horse adoption journey commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.repositories.player_repository import CandidateRecord, PlayerRecord

from .candidate_generator import generate_candidate_horses


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


def start_onboarding_flow(
    repository: JsonPlayerRepository,
    user_id: int,
    guild_id: int | None,
    display_name: str,
    candidate_seed: int | str | None = None,
    candidate_generator: Callable[[int | str | None], list[CandidateRecord]] = generate_candidate_horses,
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
