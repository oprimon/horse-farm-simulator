"""Tests for onboarding horse candidate generation."""

from pferdehof_bot.services.candidate_generator import generate_candidate_horses


def test_generate_candidate_horses_returns_exactly_three_with_abc_ids() -> None:
    candidates = generate_candidate_horses(seed=20260322)

    assert len(candidates) == 3
    assert {candidate["id"] for candidate in candidates} == {"A", "B", "C"}


def test_generate_candidate_horses_is_deterministic_for_same_seed() -> None:
    first = generate_candidate_horses(seed=1337)
    second = generate_candidate_horses(seed=1337)

    assert first == second
