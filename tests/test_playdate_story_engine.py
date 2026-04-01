"""Tests for playdate story engine narrative rendering."""

from __future__ import annotations

import random

from pferdehof_bot.services.playdate_story_engine import PlaydateStoryContext, render_playdate_narrative


def _context() -> PlaydateStoryContext:
    return PlaydateStoryContext(
        initiator_horse_name="Nova",
        target_horse_name="Luna",
        initiator_player_name="Mia",
        target_player_name="Rowan",
        initiator_energy=74,
        target_energy=24,
        initiator_confidence=60,
        target_confidence=20,
        initiator_bond=70,
        target_bond=68,
        initiator_health=80,
        target_health=77,
    )


def test_render_playdate_narrative_includes_stat_reactive_low_energy_and_low_confidence_lines() -> None:
    narrative = render_playdate_narrative(
        _context(),
        rng=random.Random(5),
        story_id_override="apple_diplomacy",
        cameo_override="none",
    )

    assert narrative.story_id == "apple_diplomacy"
    assert "Although a little tired, Luna" in narrative.message or "Even while winded, Luna" in narrative.message
    assert "Luna pauses once" in narrative.message or "After one careful glance around, Luna" in narrative.message


def test_render_playdate_narrative_can_include_both_players_in_cameo() -> None:
    narrative = render_playdate_narrative(
        _context(),
        rng=random.Random(9),
        story_id_override="brush_conspiracy",
        cameo_override="both",
    )

    assert narrative.story_id == "brush_conspiracy"
    assert "Mia" in narrative.message
    assert "Rowan" in narrative.message


def test_render_playdate_narrative_can_include_single_player_cameo() -> None:
    narrative = render_playdate_narrative(
        _context(),
        rng=random.Random(12),
        story_id_override="puddle_sprint",
        cameo_override="one",
    )

    assert narrative.story_id == "puddle_sprint"
    assert ("Mia" in narrative.message) or ("Rowan" in narrative.message)
