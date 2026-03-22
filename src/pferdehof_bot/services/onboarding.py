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
