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

_SKILL_KEYS: tuple[str, ...] = (
    "bond",
    "energy",
    "health",
    "confidence",
    "skill",
)

_SKILL_VALUE_POOL: tuple[tuple[int, int], ...] = (
    (2, 3),
    (3, 6),
    (4, 10),
    (5, 14),
    (6, 10),
    (7, 6),
    (8, 3),
)

_HINT_BY_PRIMARY_SKILL: dict[str, tuple[str, ...]] = {
    "bond": (
        "Seems eager to connect with one person.",
        "Leans in gently when someone approaches.",
    ),
    "energy": (
        "Looks eager to move and explore.",
        "Has a lively spark in every step.",
    ),
    "health": (
        "Carries a strong, steady presence.",
        "Looks robust and well-balanced.",
    ),
    "confidence": (
        "Keeps calm even in unfamiliar moments.",
        "Holds posture like little surprises do not bother them.",
    ),
    "skill": (
        "Seems quick to understand new routines.",
        "Watches closely, like learning comes naturally.",
    ),
}


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
    skills = _build_skills(rng)
    hint = _derive_hint_from_skills(skills=skills, rng=rng)

    return {
        "id": candidate_id,
        "coat": coat,
        "marking": marking,
        "appearance_text": f"{coat} {marking}",
        "hint": hint,
        "template_seed": rng.getrandbits(32),
        "hidden": {
            "skills": skills,
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


def _build_skills(rng: Random) -> dict[str, int]:
    skills: dict[str, int] = {}
    for skill_key in _SKILL_KEYS:
        skills[skill_key] = _weighted_pick_int(_SKILL_VALUE_POOL, rng)
    return skills


def _weighted_pick_int(weighted_pool: tuple[tuple[int, int], ...], rng: Random) -> int:
    total_weight = sum(weight for _, weight in weighted_pool)
    roll = rng.uniform(0, total_weight)
    running_total = 0.0

    for value, weight in weighted_pool:
        running_total += weight
        if roll <= running_total:
            return value

    return weighted_pool[-1][0]


def _derive_hint_from_skills(skills: dict[str, int], rng: Random) -> str:
    # Pick the strongest skill, with deterministic tie-break order from _SKILL_KEYS.
    strongest_key = max(_SKILL_KEYS, key=lambda key: skills[key])
    options = _HINT_BY_PRIMARY_SKILL[strongest_key]
    return options[rng.randrange(len(options))]


def _is_duplicate_visible_profile(candidate: CandidateRecord, existing: list[CandidateRecord]) -> bool:
    visible_profile = (candidate["appearance_text"], candidate["hint"])
    for existing_candidate in existing:
        if (existing_candidate["appearance_text"], existing_candidate["hint"]) == visible_profile:
            return True
    return False
