"""Player-facing horse state text mapping for profile and loop commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class HorseStatePresentation:
    """Human-readable state labels derived from internal horse progression values."""

    readiness_feel: str
    bond_feel: str
    energy_feel: str
    confidence_feel: str
    skill_feel: str
    recent_activity_text: str | None


def build_horse_state_presentation(horse: Mapping[str, Any]) -> HorseStatePresentation:
    """Build a reusable player-facing view of horse progression state."""
    energy = _normalize_state_value(horse.get("energy"), default=70)
    health = _normalize_state_value(horse.get("health"), default=75)
    bond = _normalize_state_value(horse.get("bond"), default=25)
    confidence = _normalize_state_value(horse.get("confidence"), default=35)
    skill = _normalize_state_value(horse.get("skill"), default=10)
    recent_activity = _normalize_optional_text(horse.get("recent_activity"))

    return HorseStatePresentation(
        readiness_feel=_readiness_feel(energy=energy, health=health, confidence=confidence),
        bond_feel=_band_text(
            value=bond,
            low="still learning your rhythm",
            mid="steady and trusting",
            high="deeply connected and affectionate",
        ),
        energy_feel=_band_text(
            value=energy,
            low="running low and needs rest",
            mid="comfortable and ready for gentle activity",
            high="bright-eyed and eager to move",
        ),
        confidence_feel=_band_text(
            value=confidence,
            low="a little unsure and needs reassurance",
            mid="calmly brave and cooperative",
            high="bold and excited to try new things",
        ),
        skill_feel=_band_text(
            value=skill,
            low="just starting the basics",
            mid="building good habits and balance",
            high="showing polished progress in training",
        ),
        recent_activity_text=recent_activity,
    )


def _readiness_feel(energy: int, health: int, confidence: int) -> str:
    if energy < 30 or health < 35:
        return "tired and asks for an easy, caring day"
    if confidence >= 65 and energy >= 65 and health >= 60:
        return "eager and ready for a confident outing"
    if confidence < 30:
        return "gentle but cautious, looking to you for guidance"
    return "steady and happy to spend time together"


def _band_text(value: int, low: str, mid: str, high: str) -> str:
    if value <= 33:
        return low
    if value <= 66:
        return mid
    return high


def _normalize_state_value(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(100, parsed))


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None