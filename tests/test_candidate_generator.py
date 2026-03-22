"""Tests for onboarding horse candidate generation."""

from pferdehof_bot.services.candidate_generator import generate_candidate_horses


def test_generate_candidate_horses_returns_exactly_three_with_abc_ids() -> None:
    candidates = generate_candidate_horses(seed=20260322)

    assert len(candidates) == 3
    assert {candidate["id"] for candidate in candidates} == {"A", "B", "C"}
    for candidate in candidates:
        assert isinstance(candidate["coat"], str)
        assert isinstance(candidate["marking"], str)
        assert isinstance(candidate["appearance_text"], str)
        assert isinstance(candidate["hint"], str)
        assert candidate["hint"]


def test_generate_candidate_horses_includes_hidden_skill_properties() -> None:
    candidates = generate_candidate_horses(seed=99)

    for candidate in candidates:
        hidden = candidate["hidden"]
        skills = hidden["skills"]

        assert set(skills.keys()) == {"bond", "energy", "health", "confidence", "skill"}
        for value in skills.values():
            assert isinstance(value, int)
            assert 2 <= value <= 8


def test_generate_candidate_horses_is_deterministic_for_same_seed() -> None:
    first = generate_candidate_horses(seed=1337)
    second = generate_candidate_horses(seed=1337)

    assert first == second
