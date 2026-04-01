"""Tests for playdate story engine narrative rendering."""

from __future__ import annotations

import json
from pathlib import Path
import random

from pferdehof_bot.services.playdate_story_engine import (
    PlaydateStoryContext,
    load_story_packs_from_folder,
    render_playdate_narrative,
)


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


def test_load_story_packs_from_folder_loads_valid_json(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    (stories_dir / "test.json").write_text(
        json.dumps({
            "stories": [{
                "story_id": "test_story",
                "tone": "funny",
                "title": "Test Story",
                "weight": 5,
                "opening_lines": ["Opening line."],
                "event_lines": ["Event line."],
                "ending_lines": ["Ending line."],
                "cameo_none_lines": ["No cameo."],
                "cameo_one_lines": ["{one_player} appears."],
                "cameo_both_lines": ["{initiator_player} and {target_player} watch."],
            }]
        }),
        encoding="utf-8",
    )
    stories = load_story_packs_from_folder(stories_dir)
    assert len(stories) == 1
    assert stories[0].story_id == "test_story"
    assert stories[0].tone == "funny"
    assert stories[0].weight == 5


def test_load_story_packs_from_folder_returns_empty_for_missing_folder(tmp_path: Path) -> None:
    stories = load_story_packs_from_folder(tmp_path / "nonexistent")
    assert stories == ()


def test_load_story_packs_from_folder_skips_malformed_files(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    (stories_dir / "bad.json").write_text("not valid json", encoding="utf-8")
    stories = load_story_packs_from_folder(stories_dir)
    assert stories == ()


def test_load_story_packs_from_folder_skips_malformed_entries(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    (stories_dir / "mixed.json").write_text(
        json.dumps({
            "stories": [
                {"story_id": "good", "tone": "cozy", "title": "Good", "weight": 7,
                 "opening_lines": ["Hello."], "event_lines": ["Event."], "ending_lines": ["End."],
                 "cameo_none_lines": ["None."], "cameo_one_lines": ["One."], "cameo_both_lines": ["Both."]},
                {"missing_required_fields": True},
            ]
        }),
        encoding="utf-8",
    )
    stories = load_story_packs_from_folder(stories_dir)
    assert len(stories) == 1
    assert stories[0].story_id == "good"


def test_render_playdate_narrative_uses_folder_stories_when_provided(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    (stories_dir / "custom.json").write_text(
        json.dumps({
            "stories": [{
                "story_id": "custom_story",
                "tone": "cozy",
                "title": "Custom Story",
                "weight": 10,
                "opening_lines": ["{initiator_horse} and {target_horse} meet."],
                "event_lines": ["Things happen."],
                "ending_lines": ["All is well."],
                "cameo_none_lines": ["Nobody notices."],
                "cameo_one_lines": ["{one_player} waves."],
                "cameo_both_lines": ["{initiator_player} and {target_player} cheer."],
            }]
        }),
        encoding="utf-8",
    )
    narrative = render_playdate_narrative(
        _context(),
        rng=random.Random(1),
        story_packs_dir=stories_dir,
    )
    assert narrative.story_id == "custom_story"
    assert narrative.tone == "cozy"


def _bad_placeholder_entry(story_id: str, bad_field: str, bad_line: str) -> dict:
    base = {
        "story_id": story_id, "tone": "funny", "title": "T", "weight": 5,
        "opening_lines": ["Opening."], "event_lines": ["Event."], "ending_lines": ["End."],
        "cameo_none_lines": ["None."], "cameo_one_lines": ["{one_player} waves."],
        "cameo_both_lines": ["{initiator_player} and {target_player} cheer."],
    }
    base[bad_field] = [bad_line]
    return base


def test_load_story_packs_skips_entry_with_one_player_in_opening_lines(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    (stories_dir / "bad.json").write_text(
        json.dumps({"stories": [
            _bad_placeholder_entry(
                "bad_story", "opening_lines",
                "{initiator_horse} and {one_player} open the show.",  # one_player illegal here
            )
        ]}),
        encoding="utf-8",
    )
    stories = load_story_packs_from_folder(stories_dir)
    assert stories == ()


def test_load_story_packs_skips_entry_with_horse_name_in_cameo_lines(tmp_path: Path) -> None:
    stories_dir = tmp_path / "stories"
    stories_dir.mkdir()
    (stories_dir / "bad.json").write_text(
        json.dumps({"stories": [
            _bad_placeholder_entry(
                "bad_cameo", "cameo_none_lines",
                "{initiator_horse} approves.",  # horse placeholder illegal in cameo field
            )
        ]}),
        encoding="utf-8",
    )
    stories = load_story_packs_from_folder(stories_dir)
    assert stories == ()

