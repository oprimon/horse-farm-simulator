"""Tests for horse state text mapping service."""

from __future__ import annotations

from pferdehof_bot.services.state_presentation import build_horse_state_presentation


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
    assert presentation.bond_value == 15
    assert presentation.energy_value == 10
    assert presentation.health_value == 20
    assert presentation.confidence_value == 20
    assert presentation.skill_value == 12
    assert presentation.bond_feel == "still learning your rhythm"
    assert presentation.energy_feel == "running low and needs rest"
    assert presentation.health_feel == "a bit fragile and needs careful recovery"
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
    assert presentation.bond_value == 45
    assert presentation.energy_value == 60
    assert presentation.health_value == 70
    assert presentation.confidence_value == 50
    assert presentation.skill_value == 60
    assert presentation.bond_feel == "steady and trusting"
    assert presentation.energy_feel == "comfortable and ready for gentle activity"
    assert presentation.health_feel == "strong and in great shape"
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
    assert presentation.bond_value == 95
    assert presentation.energy_value == 90
    assert presentation.health_value == 85
    assert presentation.confidence_value == 88
    assert presentation.skill_value == 80
    assert presentation.bond_feel == "deeply connected and affectionate"
    assert presentation.energy_feel == "bright-eyed and eager to move"
    assert presentation.health_feel == "strong and in great shape"
    assert presentation.confidence_feel == "bold and excited to try new things"
    assert presentation.skill_feel == "showing polished progress in training"
    assert presentation.recent_activity_text is None