"""Tests for horse state text mapping service."""

from __future__ import annotations

from pferdehof_bot.services import build_horse_state_presentation


def test_state_presentation_maps_low_bands_and_tired_readiness() -> None:
    presentation = build_horse_state_presentation(
        {
            "energy": 10,
            "health": 20,
            "bond": 15,
            "confidence": 20,
            "skill": 12,
            "recent_activity": "",
        }
    )

    assert presentation.readiness_feel == "tired and asks for an easy, caring day"
    assert presentation.bond_feel == "still learning your rhythm"
    assert presentation.energy_feel == "running low and needs rest"
    assert presentation.confidence_feel == "a little unsure and needs reassurance"
    assert presentation.skill_feel == "just starting the basics"
    assert presentation.recent_activity_text is None


def test_state_presentation_maps_mid_bands_and_steady_readiness() -> None:
    presentation = build_horse_state_presentation(
        {
            "energy": 60,
            "health": 70,
            "bond": 45,
            "confidence": 50,
            "skill": 60,
            "recent_activity": "Had a calm brushing session.",
        }
    )

    assert presentation.readiness_feel == "steady and happy to spend time together"
    assert presentation.bond_feel == "steady and trusting"
    assert presentation.energy_feel == "comfortable and ready for gentle activity"
    assert presentation.confidence_feel == "calmly brave and cooperative"
    assert presentation.skill_feel == "building good habits and balance"
    assert presentation.recent_activity_text == "Had a calm brushing session."


def test_state_presentation_maps_high_bands_and_eager_readiness() -> None:
    presentation = build_horse_state_presentation(
        {
            "energy": 90,
            "health": 85,
            "bond": 95,
            "confidence": 88,
            "skill": 80,
        }
    )

    assert presentation.readiness_feel == "eager and ready for a confident outing"
    assert presentation.bond_feel == "deeply connected and affectionate"
    assert presentation.energy_feel == "bright-eyed and eager to move"
    assert presentation.confidence_feel == "bold and excited to try new things"
    assert presentation.skill_feel == "showing polished progress in training"
    assert presentation.recent_activity_text is None