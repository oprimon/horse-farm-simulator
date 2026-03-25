"""Unit tests for the ride outcome engine (T09)."""

from __future__ import annotations

import random

import pytest

from pferdehof_bot.services.ride_outcomes import (
    RideOutcomeEntry,
    RideOutcomeResult,
    _CATEGORY_WEIGHTS_BY_BAND,
    _OUTCOME_TABLES,
    all_outcome_entries,
    compute_readiness_score,
    select_ride_outcome,
)


# ---------------------------------------------------------------------------
# compute_readiness_score
# ---------------------------------------------------------------------------

def test_readiness_score_uses_correct_weights() -> None:
    # energy=100, rest 0 => 0.30 * 100 = 30
    assert compute_readiness_score(energy=100, confidence=0, bond=0, skill=0) == pytest.approx(30.0)
    # confidence=100, rest 0
    assert compute_readiness_score(energy=0, confidence=100, bond=0, skill=0) == pytest.approx(30.0)
    # bond=100, rest 0
    assert compute_readiness_score(energy=0, confidence=0, bond=100, skill=0) == pytest.approx(20.0)
    # skill=100, rest 0
    assert compute_readiness_score(energy=0, confidence=0, bond=0, skill=100) == pytest.approx(20.0)


def test_readiness_score_max_is_100() -> None:
    score = compute_readiness_score(energy=100, confidence=100, bond=100, skill=100)
    assert score == pytest.approx(100.0)


def test_readiness_score_min_is_0() -> None:
    score = compute_readiness_score(energy=0, confidence=0, bond=0, skill=0)
    assert score == pytest.approx(0.0)


def test_readiness_score_clamps_over_range_inputs() -> None:
    # Over-range values are clamped to 100.
    score_clamped = compute_readiness_score(energy=200, confidence=200, bond=200, skill=200)
    score_max = compute_readiness_score(energy=100, confidence=100, bond=100, skill=100)
    assert score_clamped == pytest.approx(score_max)


def test_readiness_score_clamps_negative_inputs() -> None:
    score = compute_readiness_score(energy=-50, confidence=-50, bond=-50, skill=-50)
    assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Outcome content tables - structural integrity
# ---------------------------------------------------------------------------

def test_all_outcome_entries_returns_every_entry() -> None:
    entries = all_outcome_entries()
    # Must have entries in all four categories.
    categories = {e.category for e in entries}
    assert categories == {"excellent", "good", "fair", "setback"}


def test_every_entry_has_required_fields() -> None:
    for entry in all_outcome_entries():
        assert isinstance(entry, RideOutcomeEntry)
        assert entry.outcome_id
        assert entry.category in {"excellent", "good", "fair", "setback"}
        assert entry.story_text
        assert entry.recent_activity_text


def test_every_entry_id_is_unique() -> None:
    ids = [e.outcome_id for e in all_outcome_entries()]
    assert len(ids) == len(set(ids)), "Duplicate outcome_id detected"


def test_horse_name_placeholder_present_in_all_templates() -> None:
    for entry in all_outcome_entries():
        assert "{horse_name}" in entry.story_text, (
            f"outcome_id={entry.outcome_id!r} story_text missing {{horse_name}}"
        )
        assert "{horse_name}" in entry.recent_activity_text, (
            f"outcome_id={entry.outcome_id!r} recent_activity_text missing {{horse_name}}"
        )


def test_weight_tables_cover_all_bands() -> None:
    expected_bands = {"high", "medium_high", "medium_low", "low"}
    assert set(_CATEGORY_WEIGHTS_BY_BAND.keys()) == expected_bands


def test_weight_tables_cover_all_categories_per_band() -> None:
    expected_categories = {"excellent", "good", "fair", "setback"}
    for band, rows in _CATEGORY_WEIGHTS_BY_BAND.items():
        categories_in_band = {cat for cat, _ in rows}
        assert categories_in_band == expected_categories, (
            f"Band '{band}' missing categories: {expected_categories - categories_in_band}"
        )


def test_weight_tables_have_positive_total_weight_per_band() -> None:
    for band, rows in _CATEGORY_WEIGHTS_BY_BAND.items():
        total = sum(w for _, w in rows)
        assert total > 0, f"Band '{band}' has zero total weight"


# ---------------------------------------------------------------------------
# select_ride_outcome – determinism and field population
# ---------------------------------------------------------------------------

def test_select_ride_outcome_returns_ride_outcome_result() -> None:
    result = select_ride_outcome(
        horse_name="Luna",
        energy=70,
        confidence=70,
        bond=60,
        skill=50,
    )
    assert isinstance(result, RideOutcomeResult)


def test_select_ride_outcome_fills_horse_name_into_story_text() -> None:
    result = select_ride_outcome(
        horse_name="Solaris",
        energy=60,
        confidence=60,
        bond=50,
        skill=40,
    )
    assert "Solaris" in result.story_text
    assert "Solaris" in result.recent_activity_text


def test_select_ride_outcome_is_deterministic_with_seeded_rng() -> None:
    rng_a = random.Random(42)
    rng_b = random.Random(42)

    result_a = select_ride_outcome(
        horse_name="Blaze",
        energy=55,
        confidence=55,
        bond=45,
        skill=35,
        rng=rng_a,
    )
    result_b = select_ride_outcome(
        horse_name="Blaze",
        energy=55,
        confidence=55,
        bond=45,
        skill=35,
        rng=rng_b,
    )
    assert result_a.outcome_id == result_b.outcome_id
    assert result_a.category == result_b.category
    assert result_a.story_text == result_b.story_text


def test_select_ride_outcome_different_seeds_can_yield_different_results() -> None:
    # Generate 50 outcomes for mid-range state to confirm multiple categories appear.
    seen_categories: set[str] = set()
    for seed in range(50):
        result = select_ride_outcome(
            horse_name="Nova",
            energy=50,
            confidence=50,
            bond=50,
            skill=50,
            rng=random.Random(seed),
        )
        seen_categories.add(result.category)
    # At score ~50, at least 2 different categories should appear over 50 seeds.
    assert len(seen_categories) >= 2


# ---------------------------------------------------------------------------
# select_ride_outcome – category weighting per state band
# ---------------------------------------------------------------------------

def test_high_readiness_predominantly_yields_excellent_or_good() -> None:
    """High-state horses should not give setback outcomes in normal sampling."""
    setback_count = 0
    for seed in range(100):
        result = select_ride_outcome(
            horse_name="Aria",
            energy=90,
            confidence=90,
            bond=80,
            skill=80,
            rng=random.Random(seed),
        )
        if result.category == "setback":
            setback_count += 1
    # Setback weight is 1 % for the high band; over 100 seeds almost none expected.
    assert setback_count <= 5


def test_high_readiness_yields_at_least_some_excellent_outcomes() -> None:
    excellent_count = 0
    for seed in range(100):
        result = select_ride_outcome(
            horse_name="Aria",
            energy=90,
            confidence=90,
            bond=80,
            skill=80,
            rng=random.Random(seed),
        )
        if result.category == "excellent":
            excellent_count += 1
    # Excellent weight is 60 % for high band; expect at least 40/100.
    assert excellent_count >= 40


def test_low_readiness_predominantly_yields_setback_or_fair() -> None:
    poor_ride_count = 0
    for seed in range(100):
        result = select_ride_outcome(
            horse_name="Shadow",
            energy=10,
            confidence=10,
            bond=10,
            skill=5,
            rng=random.Random(seed),
        )
        if result.category in {"setback", "fair"}:
            poor_ride_count += 1
    # Low band: setback=50%, fair=40% => 90% combined; expect at least 80/100.
    assert poor_ride_count >= 80


def test_low_readiness_never_yields_excellent() -> None:
    for seed in range(200):
        result = select_ride_outcome(
            horse_name="Shadow",
            energy=0,
            confidence=0,
            bond=0,
            skill=0,
            rng=random.Random(seed),
        )
        assert result.category != "excellent", (
            f"seed={seed}: low-state horse should not yield excellent outcome"
        )


def test_medium_high_readiness_mostly_good_or_better() -> None:
    good_or_better = 0
    for seed in range(100):
        result = select_ride_outcome(
            horse_name="Thorn",
            energy=60,
            confidence=55,
            bond=50,
            skill=40,
            rng=random.Random(seed),
        )
        if result.category in {"excellent", "good"}:
            good_or_better += 1
    # excellent=20%, good=50% => 70%; at least 55/100 expected.
    assert good_or_better >= 55


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_select_ride_outcome_handles_max_state() -> None:
    result = select_ride_outcome(
        horse_name="Champion",
        energy=100,
        confidence=100,
        bond=100,
        skill=100,
    )
    assert result.category in {"excellent", "good", "fair", "setback"}
    assert result.outcome_id


def test_select_ride_outcome_handles_zero_state() -> None:
    result = select_ride_outcome(
        horse_name="Phantom",
        energy=0,
        confidence=0,
        bond=0,
        skill=0,
    )
    assert result.category in {"fair", "setback"}
    assert result.outcome_id


def test_outcome_tables_have_at_least_two_entries_per_category() -> None:
    for category, table in _OUTCOME_TABLES.items():
        assert len(table) >= 2, (
            f"Category '{category}' has fewer than 2 outcome entries"
        )
