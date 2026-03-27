"""Player-facing horse state text mapping for profile and loop commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class StateEmbedField:
    """A single Discord-agnostic embed field fragment for rendering."""

    name: str
    value: str
    inline: bool = False


@dataclass(frozen=True)
class HorseStatePresentation:
    """Human-readable state labels derived from internal horse progression values."""

    bond_value: int
    energy_value: int
    health_value: int
    confidence_value: int
    skill_value: int
    readiness_feel: str
    bond_feel: str
    energy_feel: str
    health_feel: str
    confidence_feel: str
    skill_feel: str
    recent_activity_text: str | None

    @property
    def embed_fields(self) -> tuple[StateEmbedField, ...]:
        """Structured field fragments ready for embed rendering."""
        return (
            StateEmbedField(name="Mood", value=self.readiness_feel),
            StateEmbedField(name=f"Bond ({self.bond_value})", value=self.bond_feel, inline=True),
            StateEmbedField(name=f"Energy ({self.energy_value})", value=self.energy_feel, inline=True),
            StateEmbedField(name=f"Health ({self.health_value})", value=self.health_feel, inline=True),
            StateEmbedField(name=f"Confidence ({self.confidence_value})", value=self.confidence_feel, inline=True),
            StateEmbedField(name=f"Skill ({self.skill_value})", value=self.skill_feel, inline=True),
            StateEmbedField(
                name="Recent Activity",
                value=(
                    self.recent_activity_text
                    if self.recent_activity_text is not None
                    else "Nothing recent yet - try a cozy interaction like `/greet`."
                ),
            ),
        )


def build_horse_state_presentation(horse: Mapping[str, Any]) -> HorseStatePresentation:
    """Build a reusable player-facing view of horse progression state."""
    energy = _normalize_state_value(horse.get("energy"), default=70)
    health = _normalize_state_value(horse.get("health"), default=75)
    bond = _normalize_state_value(horse.get("bond"), default=25)
    confidence = _normalize_state_value(horse.get("confidence"), default=35)
    skill = _normalize_state_value(horse.get("skill"), default=10)
    recent_activity = _normalize_optional_text(horse.get("recent_activity"))

    return HorseStatePresentation(
        bond_value=bond,
        energy_value=energy,
        health_value=health,
        confidence_value=confidence,
        skill_value=skill,
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
        health_feel=_band_text(
            value=health,
            low="a bit fragile and needs careful recovery",
            mid="recovering well and staying steady",
            high="strong and in great shape",
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