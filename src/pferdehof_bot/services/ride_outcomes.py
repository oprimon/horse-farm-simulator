"""Ride outcome engine with weighted story selection based on horse state.

The engine computes a readiness score from horse state dimensions, then picks
a weighted outcome category (excellent / good / fair / setback) and draws a
story entry from the matching content table.  All randomness is injectable for
deterministic testing.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Sequence


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RideOutcomeEntry:
    """A single named ride story with narrative copy templates."""

    outcome_id: str
    """Stable identifier used in telemetry and tests."""

    category: str
    """One of 'excellent', 'good', 'fair', or 'setback'."""

    story_text: str
    """Main response shown to the player.  Use ``{horse_name}`` placeholder."""

    recent_activity_text: str
    """Short summary that goes into the horse's recent-activity slot.  Use ``{horse_name}``."""


@dataclass(frozen=True)
class RideOutcomeResult:
    """Result of a ride outcome selection, ready to be rendered and persisted."""

    outcome_id: str
    category: str
    story_text: str
    recent_activity_text: str


# ---------------------------------------------------------------------------
# Content tables
# ---------------------------------------------------------------------------

_EXCELLENT_OUTCOMES: tuple[RideOutcomeEntry, ...] = (
    RideOutcomeEntry(
        outcome_id="windswept_gallop",
        category="excellent",
        story_text=(
            "{horse_name} stretches out into a full, joyful gallop the moment you ask. "
            "The fields blur past, the wind fills your lungs, and for a brief shining moment "
            "it feels like nothing in the world could slow you down. "
            "You can feel how much {horse_name} trusts you through every stride."
        ),
        recent_activity_text=(
            "You and {horse_name} shared a breathtaking gallop - pure trust and joy at full speed."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="picture_perfect_canter",
        category="excellent",
        story_text=(
            "The canter today is everything: soft, rhythmic, and completely in sync. "
            "{horse_name} carries you effortlessly, ears pricked and neck arched, "
            "as if putting on a performance just for you. "
            "Every transition lands exactly where you ask for it."
        ),
        recent_activity_text=(
            "A flowing, picture-perfect canter with {horse_name} — every step was in harmony."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="confident_obstacle",
        category="excellent",
        story_text=(
            "You guide {horse_name} toward a low obstacle on the trail and feel "
            "no hesitation whatsoever - just a calm, collected pop over the top. "
            "{horse_name} lands softly, shakes their neck, and immediately looks for the next one. "
            "All those careful training sessions are clearly paying off."
        ),
        recent_activity_text=(
            "{horse_name} tackled a trail obstacle without a hint of doubt - confident and tidy."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="deep_connection_ride",
        category="excellent",
        story_text=(
            "Today's ride feels like a conversation. "
            "{horse_name} responds to the lightest aids, anticipates your intent, "
            "and even nuzzles your knee gently when you pause on a hillside. "
            "This is what all the patient care and training has been building toward."
        ),
        recent_activity_text=(
            "A deeply connected ride with {horse_name} - the bond between you felt unmistakable."
        ),
    ),
)

_GOOD_OUTCOMES: tuple[RideOutcomeEntry, ...] = (
    RideOutcomeEntry(
        outcome_id="steady_trot",
        category="good",
        story_text=(
            "{horse_name} moves into a steady, forward trot and maintains it beautifully "
            "through all four corners of the field. "
            "A confident horse, a willing partner - not every ride needs to be a fairytale "
            "to be a good one."
        ),
        recent_activity_text=(
            "A reliable, happy trot through the fields with {horse_name} - solid and satisfying."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="trail_exploration",
        category="good",
        story_text=(
            "You take {horse_name} on a relaxed trail loop you have not tried before. "
            "There is one moment where {horse_name} pauses to sniff at a fallen log, "
            "ears swivelling curiously - and then calmly steps right over it. "
            "Brave enough to explore, sensible enough to stay settled. That is the heart of it."
        ),
        recent_activity_text=(
            "{horse_name} explored a new trail with you - curious, sensible, and good company."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="relaxed_warm_down",
        category="good",
        story_text=(
            "After a cheerful working session, you let {horse_name} walk on a long rein. "
            "{horse_name} blows out a slow breath, drops their nose, and stretches contentedly. "
            "It is a quiet, warm finish - and both of you feel well spent in the best possible way."
        ),
        recent_activity_text=(
            "A rewarding session and a long, peaceful warm-down walk with {horse_name}."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="building_confidence",
        category="good",
        story_text=(
            "There is a moment midway through the ride when something rustles in the hedge. "
            "{horse_name} wavers for a heartbeat, then chooses to trust you completely. "
            "You feel that choice through the reins: a small leap of faith, quietly taken. "
            "Days like this are how horses grow."
        ),
        recent_activity_text=(
            "{horse_name} worked through a small worry and chose trust — a meaningful moment."
        ),
    ),
)

_FAIR_OUTCOMES: tuple[RideOutcomeEntry, ...] = (
    RideOutcomeEntry(
        outcome_id="short_but_sweet",
        category="fair",
        story_text=(
            "The ride is shorter than you planned but still full of quiet warmth. "
            "{horse_name} is a little tired, so you keep it easy and end on a soft, "
            "willing note. Sometimes the kindest ride is a gentle one."
        ),
        recent_activity_text=(
            "A gentle, short ride with {horse_name} - kept easy and ended on a willing note."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="learning_moment",
        category="fair",
        story_text=(
            "Midway through, {horse_name} drifts off the line and you spend a few minutes "
            "quietly insisting on straightness. It is not dramatic, just patient correction and "
            "a small breakthrough when {horse_name} gets it right. "
            "These are the sessions that quietly build the foundation."
        ),
        recent_activity_text=(
            "{horse_name} needed some patient guidance today - but finished the session well."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="tired_but_willing",
        category="fair",
        story_text=(
            "{horse_name} is running lower than usual on energy, but keeps trying earnestly "
            "right up until you decide to call it and head home. "
            "You appreciate that willingness more than you could say. "
            "A rest day tomorrow seems like a kind reward."
        ),
        recent_activity_text=(
            "{horse_name} rode earnestly despite being tired - a rest day is well earned."
        ),
    ),
)

_SETBACK_OUTCOMES: tuple[RideOutcomeEntry, ...] = (
    RideOutcomeEntry(
        outcome_id="spook_and_recover",
        category="setback",
        story_text=(
            "A bird shoots out of the grass and {horse_name} startles sideways with a snort. "
            "Your heart jolts, but you stay calm and your steadiness steadies them. "
            "After a quiet moment and some reassuring pats, {horse_name} settles - "
            "a little shaky, but willing to walk on. "
            "Today was about staying safe, and you did."
        ),
        recent_activity_text=(
            "{horse_name} spooked on the trail but recovered safely with your steady support."
        ),
    ),
    RideOutcomeEntry(
        outcome_id="called_it_early",
        category="setback",
        story_text=(
            "Something about today feels off. {horse_name} moves stiffly at first, "
            "reluctant and distracted, and you trust that signal. "
            "You turn for home early, untack quietly, and spend a few extra minutes with brushes. "
            "Knowing when to listen is part of being a good partner. "
            "Some days are for caring, not riding."
        ),
        recent_activity_text=(
            "You read {horse_name}'s mood honestly and ended the ride early - quiet care followed."
        ),
    ),
)

# Keyed by category name for random sampling
_OUTCOME_TABLES: dict[str, tuple[RideOutcomeEntry, ...]] = {
    "excellent": _EXCELLENT_OUTCOMES,
    "good": _GOOD_OUTCOMES,
    "fair": _FAIR_OUTCOMES,
    "setback": _SETBACK_OUTCOMES,
}

# Weighted category tables keyed by readiness band.
# Each entry is (category, relative_weight).
_CATEGORY_WEIGHTS_BY_BAND: dict[str, list[tuple[str, int]]] = {
    # readiness >= 70
    "high": [
        ("excellent", 60),
        ("good", 33),
        ("fair", 6),
        ("setback", 1),
    ],
    # 50 <= readiness < 70
    "medium_high": [
        ("excellent", 20),
        ("good", 50),
        ("fair", 25),
        ("setback", 5),
    ],
    # 30 <= readiness < 50
    "medium_low": [
        ("excellent", 5),
        ("good", 25),
        ("fair", 50),
        ("setback", 20),
    ],
    # readiness < 30
    "low": [
        ("excellent", 0),
        ("good", 10),
        ("fair", 40),
        ("setback", 50),
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_readiness_score(
    energy: int,
    confidence: int,
    bond: int,
    skill: int,
) -> float:
    """Return a 0-100 readiness score derived from the four horse state dimensions.

    Weighting rationale: energy and confidence drive the immediate ride experience
    (30 % each), bond determines willingness to try for the rider (20 %), and
    skill affects polish more than baseline enjoyment (20 %).
    """
    e = max(0, min(100, int(energy)))
    c = max(0, min(100, int(confidence)))
    b = max(0, min(100, int(bond)))
    s = max(0, min(100, int(skill)))
    return e * 0.30 + c * 0.30 + b * 0.20 + s * 0.20


def _readiness_band(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 50:
        return "medium_high"
    if score >= 30:
        return "medium_low"
    return "low"


def select_ride_outcome(
    horse_name: str,
    energy: int,
    confidence: int,
    bond: int,
    skill: int,
    rng: random.Random | None = None,
) -> RideOutcomeResult:
    """Select a weighted ride outcome and render story text for the given horse state.

    Parameters
    ----------
    horse_name:
        The adopted horse's display name; used to fill ``{horse_name}`` placeholders.
    energy, confidence, bond, skill:
        Current horse state values (0-100).
    rng:
        Optional seeded :class:`random.Random` instance.  Pass one for
        deterministic behaviour in tests.  Falls back to the module-level RNG
        when *None*.
    """
    _rng = rng if rng is not None else random

    score = compute_readiness_score(energy=energy, confidence=confidence, bond=bond, skill=skill)
    band = _readiness_band(score)
    weight_table = _CATEGORY_WEIGHTS_BY_BAND[band]

    # Filter out zero-weight categories before sampling.
    available = [(cat, w) for cat, w in weight_table if w > 0]
    categories = [cat for cat, _ in available]
    weights = [w for _, w in available]

    chosen_category = _rng.choices(categories, weights=weights, k=1)[0]
    entry = _rng.choice(_OUTCOME_TABLES[chosen_category])

    return RideOutcomeResult(
        outcome_id=entry.outcome_id,
        category=chosen_category,
        story_text=entry.story_text.format(horse_name=horse_name),
        recent_activity_text=entry.recent_activity_text.format(horse_name=horse_name),
    )


def all_outcome_entries() -> list[RideOutcomeEntry]:
    """Return every defined outcome entry across all categories (for testing / inspection)."""
    entries: list[RideOutcomeEntry] = []
    for table in _OUTCOME_TABLES.values():
        entries.extend(table)
    return entries
