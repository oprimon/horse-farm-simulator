"""Horse candidate generation for onboarding sessions."""

from __future__ import annotations

from random import Random
from typing import Any


CandidateRecord = dict[str, Any]


_COAT_POOL: tuple[tuple[str, int], ...] = (
    ("Chestnut", 26),
    ("Bay", 24),
    ("Grey", 16),
    ("Black", 12),
    ("Palomino", 10),
    ("Dun", 7),
    ("Pinto", 5),
)

_MARKING_POOL: tuple[tuple[str, int], ...] = (
    ("with a bright blaze", 20),
    ("with white socks", 18),
    ("with a tiny star", 16),
    ("with a broad snip", 14),
    ("with a silver mane", 12),
    ("with dark stockings", 10),
    ("with dappled shoulders", 10),
)

_HINT_POOL: tuple[tuple[str, int], ...] = (
    ("Brave in new places", 16),
    ("Steady under pressure", 16),
    ("Curious around people", 14),
    ("Quick to learn routines", 14),
    ("Gentle with nervous riders", 12),
    ("Playful in the paddock", 10),
    ("Focused during training", 10),
    ("Confident with loud sounds", 8),
)


def generate_candidate_horses(seed: int | str | None = None) -> list[CandidateRecord]:
    """Generate three horse candidates with deterministic output for a fixed seed."""
    rng = Random(seed)
    candidates: list[CandidateRecord] = []

    for candidate_id in ("A", "B", "C"):
        candidate = _build_candidate(candidate_id=candidate_id, rng=rng)

        # Re-roll a small number of times to reduce identical visible profiles.
        rerolls = 0
        while rerolls < 6 and _is_duplicate_visible_profile(candidate, candidates):
            candidate = _build_candidate(candidate_id=candidate_id, rng=rng)
            rerolls += 1

        candidates.append(candidate)

    return candidates


def _build_candidate(candidate_id: str, rng: Random) -> CandidateRecord:
    coat = _weighted_pick(_COAT_POOL, rng)
    marking = _weighted_pick(_MARKING_POOL, rng)
    hint = _weighted_pick(_HINT_POOL, rng)

    return {
        "id": candidate_id,
        "appearance_text": f"{coat} {marking}",
        "hint": hint,
        "template_seed": rng.getrandbits(32),
        "hidden": {
            "coat": coat,
            "marking": marking,
            "hint_key": hint,
        },
    }


def _weighted_pick(weighted_pool: tuple[tuple[str, int], ...], rng: Random) -> str:
    total_weight = sum(weight for _, weight in weighted_pool)
    roll = rng.uniform(0, total_weight)
    running_total = 0.0

    for value, weight in weighted_pool:
        running_total += weight
        if roll <= running_total:
            return value

    return weighted_pool[-1][0]


def _is_duplicate_visible_profile(candidate: CandidateRecord, existing: list[CandidateRecord]) -> bool:
    visible_profile = (candidate["appearance_text"], candidate["hint"])
    for existing_candidate in existing:
        if (existing_candidate["appearance_text"], existing_candidate["hint"]) == visible_profile:
            return True
    return False
