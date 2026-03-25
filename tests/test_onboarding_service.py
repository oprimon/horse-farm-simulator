"""Tests for `/start` onboarding flow service."""

from __future__ import annotations

import random

from pferdehof_bot.repositories import JsonPlayerRepository
from pferdehof_bot.services import (
    admin_rename_horse_flow,
    choose_candidate_flow,
    feed_horse_flow,
    greet_horse_flow,
    groom_horse_flow,
    horse_profile_flow,
    name_horse_flow,
    rest_horse_flow,
    ride_horse_flow,
    start_onboarding_flow,
    train_horse_flow,
    view_candidates_flow,
)


def test_start_onboarding_flow_creates_session_for_new_player(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    generator_calls = 0

    def candidate_generator(seed: int | str | None):
        nonlocal generator_calls
        generator_calls += 1
        return [
            {"id": "A", "appearance_text": "Chestnut with a bright blaze", "hint": "Brave", "template_seed": 1},
            {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
            {"id": "C", "appearance_text": "Grey with a tiny star", "hint": "Curious", "template_seed": 3},
        ]

    result = start_onboarding_flow(
        repository=repository,
        user_id=111,
        guild_id=222,
        display_name="Mia",
        candidate_generator=candidate_generator,
    )

    assert generator_calls == 1
    assert result.already_adopted is False
    assert result.reused_active_session is False
    assert "/horse view" in result.message

    persisted = repository.get_player(user_id=111, guild_id=222)
    assert persisted is not None
    assert persisted["onboarding_session"]["active"] is True
    assert len(persisted["onboarding_session"]["candidates"]) == 3


def test_start_onboarding_flow_blocks_when_player_already_adopted(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with a bright blaze", "hint": "Brave", "template_seed": 11},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 12},
        {"id": "C", "appearance_text": "Grey with a tiny star", "hint": "Curious", "template_seed": 13},
    ]
    repository.start_onboarding(user_id=333, guild_id=444, candidates=candidates)
    repository.set_chosen_candidate(user_id=333, guild_id=444, candidate_id="A")
    repository.finalize_horse_name(user_id=333, guild_id=444, name="Luna")

    def should_not_run(seed: int | str | None):
        raise RuntimeError("Candidate generation should not run for adopted players")

    result = start_onboarding_flow(
        repository=repository,
        user_id=333,
        guild_id=444,
        display_name="Mia",
        candidate_generator=should_not_run,
    )

    assert result.already_adopted is True
    assert result.reused_active_session is False
    assert "already have a horse" in result.message


def test_start_onboarding_flow_is_idempotent_when_session_already_active(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    existing_candidates = [
        {"id": "A", "appearance_text": "Chestnut with a bright blaze", "hint": "Brave", "template_seed": 21},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 22},
        {"id": "C", "appearance_text": "Grey with a tiny star", "hint": "Curious", "template_seed": 23},
    ]
    repository.start_onboarding(user_id=555, guild_id=666, candidates=existing_candidates)

    generator_calls = 0

    def should_not_run(seed: int | str | None):
        nonlocal generator_calls
        generator_calls += 1
        return [
            {"id": "A", "appearance_text": "Black with dark stockings", "hint": "Steady", "template_seed": 31},
            {"id": "B", "appearance_text": "Dun with silver mane", "hint": "Bold", "template_seed": 32},
            {"id": "C", "appearance_text": "Pinto with broad snip", "hint": "Gentle", "template_seed": 33},
        ]

    result = start_onboarding_flow(
        repository=repository,
        user_id=555,
        guild_id=666,
        display_name="Mia",
        candidate_generator=should_not_run,
    )

    assert generator_calls == 0
    assert result.already_adopted is False
    assert result.reused_active_session is True
    assert "/horse view" in result.message

    persisted = repository.get_player(user_id=555, guild_id=666)
    assert persisted is not None
    assert persisted["onboarding_session"]["candidates"] == existing_candidates


def test_view_candidates_flow_fails_without_active_session(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = view_candidates_flow(
        repository=repository,
        user_id=777,
        guild_id=888,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_active_session is False
    assert result.already_adopted is False
    assert "No adoption session is active yet" in result.message
    assert "/start" in result.message


def test_view_candidates_flow_renders_candidate_payload(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=999, guild_id=111, candidates=candidates)

    result = view_candidates_flow(
        repository=repository,
        user_id=999,
        guild_id=111,
        display_name="Mia",
    )

    assert result.player is not None
    assert result.has_active_session is True
    assert result.already_adopted is False
    assert "A: Chestnut with bright blaze | Hint: Brave" in result.message
    assert "B: Bay with white socks | Hint: Calm" in result.message
    assert "C: Grey with tiny star | Hint: Curious" in result.message
    assert "/horse choose <id>" in result.message


def test_choose_candidate_flow_locks_valid_selection_and_persists(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=123, guild_id=456, candidates=candidates)

    result = choose_candidate_flow(
        repository=repository,
        user_id=123,
        guild_id=456,
        display_name="Mia",
        candidate_id="b",
    )

    assert result.invalid_candidate_id is False
    assert result.selection_locked is True
    assert result.selected_candidate_id == "B"
    assert "/horse name <name>" in result.message

    persisted = repository.get_player(user_id=123, guild_id=456)
    assert persisted is not None
    assert persisted["onboarding_session"]["chosen_candidate_id"] == "B"


def test_choose_candidate_flow_rejects_invalid_candidate_id(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=321, guild_id=654, candidates=candidates)

    result = choose_candidate_flow(
        repository=repository,
        user_id=321,
        guild_id=654,
        display_name="Mia",
        candidate_id="Z",
    )

    assert result.invalid_candidate_id is True
    assert result.selection_locked is False
    assert result.selected_candidate_id is None
    assert "Please choose A, B, or C" in result.message

    persisted = repository.get_player(user_id=321, guild_id=654)
    assert persisted is not None
    assert persisted["onboarding_session"]["chosen_candidate_id"] is None


def test_choose_candidate_flow_blocks_second_choice_when_locked(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=444, guild_id=555, candidates=candidates)
    repository.set_chosen_candidate(user_id=444, guild_id=555, candidate_id="A")

    result = choose_candidate_flow(
        repository=repository,
        user_id=444,
        guild_id=555,
        display_name="Mia",
        candidate_id="B",
    )

    assert result.invalid_candidate_id is False
    assert result.selection_locked is True
    assert result.selected_candidate_id == "A"
    assert "irreversible" in result.message

    persisted = repository.get_player(user_id=444, guild_id=555)
    assert persisted is not None
    assert persisted["onboarding_session"]["chosen_candidate_id"] == "A"


def test_name_horse_flow_rejects_name_length_boundaries(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=150, guild_id=250, candidates=candidates)
    repository.set_chosen_candidate(user_id=150, guild_id=250, candidate_id="A")

    too_short = name_horse_flow(
        repository=repository,
        user_id=150,
        guild_id=250,
        display_name="Mia",
        horse_name="A",
    )
    assert too_short.finalized is False
    assert too_short.invalid_name is True
    assert "between 2 and 20" in too_short.message

    too_long = name_horse_flow(
        repository=repository,
        user_id=150,
        guild_id=250,
        display_name="Mia",
        horse_name="A" * 21,
    )
    assert too_long.finalized is False
    assert too_long.invalid_name is True
    assert "between 2 and 20" in too_long.message


def test_name_horse_flow_rejects_profanity(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=151, guild_id=251, candidates=candidates)
    repository.set_chosen_candidate(user_id=151, guild_id=251, candidate_id="B")

    result = name_horse_flow(
        repository=repository,
        user_id=151,
        guild_id=251,
        display_name="Mia",
        horse_name="shit",
    )

    assert result.finalized is False
    assert result.invalid_name is True
    assert "cannot be used" in result.message

    persisted = repository.get_player(user_id=151, guild_id=251)
    assert persisted is not None
    assert persisted["adopted"] is False
    assert persisted["horse"] is None


def test_name_horse_flow_finalizes_adoption_and_blocks_repeated_naming(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=152, guild_id=252, candidates=candidates)
    repository.set_chosen_candidate(user_id=152, guild_id=252, candidate_id="C")

    result = name_horse_flow(
        repository=repository,
        user_id=152,
        guild_id=252,
        display_name="Mia",
        horse_name="  Luna  ",
    )

    assert result.finalized is True
    assert result.invalid_name is False
    assert "Luna is officially your horse now" in result.message
    assert "Grey with tiny star" in result.message
    assert "Curious" in result.message

    persisted = repository.get_player(user_id=152, guild_id=252)
    assert persisted is not None
    assert persisted["adopted"] is True
    assert persisted["horse"] is not None
    assert persisted["horse"]["name"] == "Luna"
    assert persisted["horse"]["appearance"] == "Grey with tiny star"
    assert persisted["horse"]["hint"] == "Curious"
    assert persisted["onboarding_session"]["active"] is False

    second_attempt = name_horse_flow(
        repository=repository,
        user_id=152,
        guild_id=252,
        display_name="Mia",
        horse_name="Nova",
    )
    assert second_attempt.finalized is False
    assert second_attempt.already_adopted is True
    assert "already adopted your horse" in second_attempt.message


def test_horse_profile_flow_guides_player_without_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = horse_profile_flow(
        repository=repository,
        user_id=700,
        guild_id=701,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert "do not have a horse yet" in result.message
    assert "/start" in result.message


def test_horse_profile_flow_renders_adopted_horse_profile(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Brave",
            "traits_visible": ["steady", "curious", "friendly"],
            "template_seed": 1,
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 2,
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Curious",
            "template_seed": 3,
        },
    ]
    repository.start_onboarding(user_id=702, guild_id=703, candidates=candidates)
    repository.set_chosen_candidate(user_id=702, guild_id=703, candidate_id="A")
    repository.finalize_horse_name(user_id=702, guild_id=703, name="Luna")
    repository.update_horse_state(
        user_id=702,
        guild_id=703,
        updates={
            "bond": 80,
            "energy": 72,
            "health": 78,
            "confidence": 68,
            "skill": 61,
            "recent_activity": "Shared a gentle arena walk.",
        },
    )

    result = horse_profile_flow(
        repository=repository,
        user_id=702,
        guild_id=703,
        display_name="Mia",
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert "Name: Luna" in result.message
    assert "Appearance: Chestnut with bright blaze" in result.message
    assert "Visible traits: steady, curious" in result.message
    assert "Mood: Luna feels eager and ready for a confident outing." in result.message
    assert "Bond: Luna is deeply connected and affectionate with you." in result.message
    assert "Energy: Luna is bright-eyed and eager to move." in result.message
    assert "Confidence: Luna is bold and excited to try new things." in result.message
    assert "Skill: Luna is building good habits and balance." in result.message
    assert "Recent activity: Shared a gentle arena walk." in result.message


def test_greet_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = greet_horse_flow(
        repository=repository,
        user_id=800,
        guild_id=801,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert "There is no horse to greet yet" in result.message
    assert "/start" in result.message


def test_greet_horse_flow_returns_personalized_response_for_adopter(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Curious",
            "template_seed": 1,
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 2,
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Brave",
            "template_seed": 3,
        },
    ]
    repository.start_onboarding(user_id=802, guild_id=803, candidates=candidates)
    repository.set_chosen_candidate(user_id=802, guild_id=803, candidate_id="A")
    repository.finalize_horse_name(user_id=802, guild_id=803, name="Luna")

    result = greet_horse_flow(
        repository=repository,
        user_id=802,
        guild_id=803,
        display_name="Mia",
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert "You greet Luna softly, Mia." in result.message
    assert "Luna steps closer" in result.message
    assert "happy to see you" in result.message


def test_feed_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = feed_horse_flow(
        repository=repository,
        user_id=820,
        guild_id=821,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.energy_gain == 0
    assert "There is no horse to feed yet" in result.message
    assert "/start" in result.message


def test_feed_horse_flow_updates_energy_and_recent_activity(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Curious",
            "template_seed": 1,
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 2,
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Brave",
            "template_seed": 3,
        },
    ]
    repository.start_onboarding(user_id=822, guild_id=823, candidates=candidates)
    repository.set_chosen_candidate(user_id=822, guild_id=823, candidate_id="A")
    repository.finalize_horse_name(user_id=822, guild_id=823, name="Luna")
    repository.update_horse_state(
        user_id=822,
        guild_id=823,
        updates={"energy": 96},
    )

    result = feed_horse_flow(
        repository=repository,
        user_id=822,
        guild_id=823,
        display_name="Mia",
        d10_roll=lambda: 7,
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.energy_gain == 7
    assert "You offer a warm feed to Luna, Mia." in result.message
    assert "+7 energy" in result.message

    persisted = repository.get_player(user_id=822, guild_id=823)
    assert persisted is not None
    assert persisted["horse"]["energy"] == 100
    assert persisted["horse"]["last_fed_at"] is not None
    assert persisted["horse"]["recent_activity"] is not None
    assert "You fed Luna" in persisted["horse"]["recent_activity"]


def test_groom_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = groom_horse_flow(
        repository=repository,
        user_id=824,
        guild_id=825,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.groomed_stat is None
    assert result.stat_gain == 0
    assert "There is no horse to groom yet" in result.message
    assert "/start" in result.message


def test_groom_horse_flow_increases_selected_stat_when_check_passes(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Curious",
            "template_seed": 1,
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 2,
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Brave",
            "template_seed": 3,
        },
    ]
    repository.start_onboarding(user_id=826, guild_id=827, candidates=candidates)
    repository.set_chosen_candidate(user_id=826, guild_id=827, candidate_id="A")
    repository.finalize_horse_name(user_id=826, guild_id=827, name="Luna")
    repository.update_horse_state(
        user_id=826,
        guild_id=827,
        updates={"bond": 95},
    )

    result = groom_horse_flow(
        repository=repository,
        user_id=826,
        guild_id=827,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: 99,
        d10_roll=lambda: 8,
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.groomed_stat == "bond"
    assert result.stat_gain == 8
    assert "You groom Luna carefully, Mia." in result.message
    assert "+8 bond" in result.message

    persisted = repository.get_player(user_id=826, guild_id=827)
    assert persisted is not None
    assert persisted["horse"]["bond"] == 100
    assert persisted["horse"]["last_groomed_at"] is not None
    assert "You groomed Luna" in str(persisted["horse"]["recent_activity"])


def test_groom_horse_flow_keeps_selected_stat_when_check_fails(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {
            "id": "A",
            "appearance_text": "Chestnut with bright blaze",
            "hint": "Curious",
            "template_seed": 1,
        },
        {
            "id": "B",
            "appearance_text": "Bay with white socks",
            "hint": "Calm",
            "template_seed": 2,
        },
        {
            "id": "C",
            "appearance_text": "Grey with tiny star",
            "hint": "Brave",
            "template_seed": 3,
        },
    ]
    repository.start_onboarding(user_id=828, guild_id=829, candidates=candidates)
    repository.set_chosen_candidate(user_id=828, guild_id=829, candidate_id="A")
    repository.finalize_horse_name(user_id=828, guild_id=829, name="Luna")
    repository.update_horse_state(
        user_id=828,
        guild_id=829,
        updates={"health": 88},
    )

    result = groom_horse_flow(
        repository=repository,
        user_id=828,
        guild_id=829,
        display_name="Mia",
        stat_selector=lambda: "health",
        d100_roll=lambda: 12,
        d10_roll=lambda: 10,
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.groomed_stat == "health"
    assert result.stat_gain == 0
    assert "quiet, comforting moment" in result.message

    persisted = repository.get_player(user_id=828, guild_id=829)
    assert persisted is not None
    assert persisted["horse"]["health"] == 88
    assert persisted["horse"]["last_groomed_at"] is not None


# ---------------------------------------------------------------------------
# T11 – admin_rename_horse_flow
# ---------------------------------------------------------------------------

def _make_adopted_repository(tmp_path, user_id: int = 900, guild_id: int = 901) -> JsonPlayerRepository:
    """Helper: create a repository with a fully adopted player."""
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Brave", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Curious", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=user_id, guild_id=guild_id, candidates=candidates)
    repository.set_chosen_candidate(user_id=user_id, guild_id=guild_id, candidate_id="A")
    repository.finalize_horse_name(user_id=user_id, guild_id=guild_id, name="Luna")
    return repository


def test_admin_rename_horse_flow_renames_adopted_horse(tmp_path) -> None:
    repository = _make_adopted_repository(tmp_path)

    result = admin_rename_horse_flow(
        repository=repository,
        admin_display_name="AdminUser",
        target_user_id=900,
        guild_id=901,
        new_name="Storm",
    )

    assert result.renamed is True
    assert result.invalid_name is False
    assert result.target_has_horse is True
    assert "Storm" in result.message

    persisted = repository.get_player(user_id=900, guild_id=901)
    assert persisted is not None
    assert persisted["horse"]["name"] == "Storm"


def test_admin_rename_horse_flow_rejects_profane_name(tmp_path) -> None:
    repository = _make_adopted_repository(tmp_path)

    result = admin_rename_horse_flow(
        repository=repository,
        admin_display_name="AdminUser",
        target_user_id=900,
        guild_id=901,
        new_name="shit",
    )

    assert result.renamed is False
    assert result.invalid_name is True
    assert result.target_has_horse is True

    persisted = repository.get_player(user_id=900, guild_id=901)
    assert persisted is not None
    assert persisted["horse"]["name"] == "Luna"


def test_admin_rename_horse_flow_rejects_name_too_short(tmp_path) -> None:
    repository = _make_adopted_repository(tmp_path)

    result = admin_rename_horse_flow(
        repository=repository,
        admin_display_name="AdminUser",
        target_user_id=900,
        guild_id=901,
        new_name="X",
    )

    assert result.renamed is False
    assert result.invalid_name is True


def test_admin_rename_horse_flow_rejects_name_too_long(tmp_path) -> None:
    repository = _make_adopted_repository(tmp_path)

    result = admin_rename_horse_flow(
        repository=repository,
        admin_display_name="AdminUser",
        target_user_id=900,
        guild_id=901,
        new_name="A" * 21,
    )

    assert result.renamed is False
    assert result.invalid_name is True


def test_admin_rename_horse_flow_fails_when_player_has_no_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = admin_rename_horse_flow(
        repository=repository,
        admin_display_name="AdminUser",
        target_user_id=999,
        guild_id=888,
        new_name="Storm",
    )

    assert result.renamed is False
    assert result.invalid_name is False
    assert result.target_has_horse is False
    assert "No adopted horse found" in result.message


# ---------------------------------------------------------------------------
# T11 – admin command permission check
# ---------------------------------------------------------------------------

def test_horse_rename_subcommand_requires_administrator_permission() -> None:
    """The horse rename subcommand must enforce administrator default permissions."""
    from pferdehof_bot.cogs.core import CoreCog

    horse_group = CoreCog.horse_group
    rename_cmd = horse_group.get_command("rename")

    assert rename_cmd is not None, "horse rename subcommand must be registered"
    assert rename_cmd.default_permissions is not None, "horse rename must include default permissions"
    assert rename_cmd.default_permissions.administrator is True


# ---------------------------------------------------------------------------
# T07 – rest_horse_flow
# ---------------------------------------------------------------------------

def _make_adopted_repo_for_rest(tmp_path, user_id: int = 930, guild_id: int = 931) -> JsonPlayerRepository:
    """Helper: create a repository with a fully adopted player."""
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Curious", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Brave", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=user_id, guild_id=guild_id, candidates=candidates)
    repository.set_chosen_candidate(user_id=user_id, guild_id=guild_id, candidate_id="A")
    repository.finalize_horse_name(user_id=user_id, guild_id=guild_id, name="Ember")
    return repository


def test_rest_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = rest_horse_flow(
        repository=repository,
        user_id=930,
        guild_id=931,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.health_gain == 0
    assert "There is no horse to rest yet" in result.message
    assert "/start" in result.message


def test_rest_horse_flow_updates_health_and_recent_activity(tmp_path) -> None:
    repository = _make_adopted_repo_for_rest(tmp_path, user_id=932, guild_id=933)
    repository.update_horse_state(
        user_id=932,
        guild_id=933,
        updates={"health": 88},
    )

    result = rest_horse_flow(
        repository=repository,
        user_id=932,
        guild_id=933,
        display_name="Mia",
        d10_roll=lambda: 6,
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.health_gain == 6
    assert "You settle Ember in for a comfortable rest, Mia." in result.message
    assert "+6 health" in result.message

    persisted = repository.get_player(user_id=932, guild_id=933)
    assert persisted is not None
    assert persisted["horse"]["health"] == 94
    assert persisted["horse"]["last_rested_at"] is not None
    assert "recent_activity" in persisted["horse"]
    assert "Ember rested quietly" in persisted["horse"]["recent_activity"]
    assert "+6 health" in persisted["horse"]["recent_activity"]


def test_rest_horse_flow_clamps_health_at_100(tmp_path) -> None:
    repository = _make_adopted_repo_for_rest(tmp_path, user_id=934, guild_id=935)
    repository.update_horse_state(
        user_id=934,
        guild_id=935,
        updates={"health": 97},
    )

    result = rest_horse_flow(
        repository=repository,
        user_id=934,
        guild_id=935,
        display_name="Mia",
        d10_roll=lambda: 10,
    )

    assert result.health_gain == 10
    persisted = repository.get_player(user_id=934, guild_id=935)
    assert persisted is not None
    assert persisted["horse"]["health"] == 100


def test_rest_horse_flow_returns_no_adopted_horse_for_unadopted_player(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Curious", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Brave", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=936, guild_id=937, candidates=candidates)

    result = rest_horse_flow(
        repository=repository,
        user_id=936,
        guild_id=937,
        display_name="Mia",
    )

    assert result.has_adopted_horse is False
    assert result.health_gain == 0
    assert "/start" in result.message


# ---------------------------------------------------------------------------
# T08 – train_horse_flow
# ---------------------------------------------------------------------------

def _make_adopted_repo_for_training(tmp_path, user_id: int = 940, guild_id: int = 941) -> JsonPlayerRepository:
    """Helper: create a repository with a fully adopted player."""
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Curious", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Brave", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=user_id, guild_id=guild_id, candidates=candidates)
    repository.set_chosen_candidate(user_id=user_id, guild_id=guild_id, candidate_id="A")
    repository.finalize_horse_name(user_id=user_id, guild_id=guild_id, name="Maple")
    return repository


def test_train_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = train_horse_flow(
        repository=repository,
        user_id=940,
        guild_id=941,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.blocked_by_readiness is False
    assert result.skill_gain == 0
    assert result.confidence_gain == 0
    assert result.energy_cost == 0
    assert result.health_loss == 0
    assert "There is no horse to train yet" in result.message
    assert "/start" in result.message


def test_train_horse_flow_refuses_when_energy_or_health_is_too_low(tmp_path) -> None:
    repository = _make_adopted_repo_for_training(tmp_path, user_id=942, guild_id=943)
    repository.update_horse_state(
        user_id=942,
        guild_id=943,
        updates={"energy": 24, "health": 80, "last_trained_at": None, "recent_activity": None},
    )

    result = train_horse_flow(
        repository=repository,
        user_id=942,
        guild_id=943,
        display_name="Mia",
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.blocked_by_readiness is True
    assert result.skill_gain == 0
    assert result.confidence_gain == 0
    assert result.energy_cost == 0
    assert result.health_loss == 0
    assert "hold off on training Maple" in result.message
    assert "/feed" in result.message
    assert "/rest" in result.message

    persisted = repository.get_player(user_id=942, guild_id=943)
    assert persisted is not None
    assert persisted["horse"]["energy"] == 24
    assert persisted["horse"]["last_trained_at"] is None
    assert persisted["horse"]["recent_activity"] is None


def test_train_horse_flow_updates_skill_confidence_and_energy(tmp_path) -> None:
    repository = _make_adopted_repo_for_training(tmp_path, user_id=944, guild_id=945)
    repository.update_horse_state(
        user_id=944,
        guild_id=945,
        updates={"skill": 20, "confidence": 30, "energy": 70, "health": 80},
    )
    d100_rolls = iter([87, 92, 14, 9])
    d10_rolls = iter([6, 4, 5])

    result = train_horse_flow(
        repository=repository,
        user_id=944,
        guild_id=945,
        display_name="Mia",
        d100_roll=lambda: next(d100_rolls),
        d10_roll=lambda: next(d10_rolls),
    )

    assert result.player is not None
    assert result.has_adopted_horse is True
    assert result.blocked_by_readiness is False
    assert result.skill_gain == 6
    assert result.confidence_gain == 4
    assert result.energy_cost == 5
    assert result.health_loss == 0
    assert "You guide Maple through a focused training session, Mia." in result.message
    assert "+6 skill, +4 confidence, -5 energy" in result.message
    assert "/ride" in result.message

    persisted = repository.get_player(user_id=944, guild_id=945)
    assert persisted is not None
    assert persisted["horse"]["skill"] == 26
    assert persisted["horse"]["confidence"] == 34
    assert persisted["horse"]["energy"] == 65
    assert persisted["horse"]["health"] == 80
    assert persisted["horse"]["last_trained_at"] is not None
    assert "You trained Maple" in str(persisted["horse"]["recent_activity"])
    assert "+6 skill" in str(persisted["horse"]["recent_activity"])
    assert "+4 confidence" in str(persisted["horse"]["recent_activity"])
    assert "-5 energy" in str(persisted["horse"]["recent_activity"])


def test_train_horse_flow_can_apply_slight_health_loss(tmp_path) -> None:
    repository = _make_adopted_repo_for_training(tmp_path, user_id=946, guild_id=947)
    repository.update_horse_state(
        user_id=946,
        guild_id=947,
        updates={"skill": 12, "confidence": 20, "energy": 50, "health": 8},
    )
    repository.update_horse_state(
        user_id=946,
        guild_id=947,
        updates={"health": 40},
    )
    d100_rolls = iter([10, 5, 91, 88])
    d10_rolls = iter([3, 7])

    result = train_horse_flow(
        repository=repository,
        user_id=946,
        guild_id=947,
        display_name="Mia",
        d100_roll=lambda: next(d100_rolls),
        d10_roll=lambda: next(d10_rolls),
    )

    assert result.blocked_by_readiness is False
    assert result.skill_gain == 0
    assert result.confidence_gain == 0
    assert result.energy_cost == 3
    assert result.health_loss == 7
    assert "-7 health" in result.message

    persisted = repository.get_player(user_id=946, guild_id=947)
    assert persisted is not None
    assert persisted["horse"]["energy"] == 47
    assert persisted["horse"]["health"] == 33
    assert "-7 health" in str(persisted["horse"]["recent_activity"])


# ---------------------------------------------------------------------------
# ride_horse_flow tests
# ---------------------------------------------------------------------------


def _make_adopted_repo_for_riding(tmp_path, user_id: int = 950, guild_id: int = 951) -> JsonPlayerRepository:
    """Helper: create a repository with a fully adopted player ready to ride."""
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")
    candidates = [
        {"id": "A", "appearance_text": "Chestnut with bright blaze", "hint": "Curious", "template_seed": 1},
        {"id": "B", "appearance_text": "Bay with white socks", "hint": "Calm", "template_seed": 2},
        {"id": "C", "appearance_text": "Grey with tiny star", "hint": "Brave", "template_seed": 3},
    ]
    repository.start_onboarding(user_id=user_id, guild_id=guild_id, candidates=candidates)
    repository.set_chosen_candidate(user_id=user_id, guild_id=guild_id, candidate_id="A")
    repository.finalize_horse_name(user_id=user_id, guild_id=guild_id, name="Maple")
    return repository


def test_ride_horse_flow_requires_adopted_horse(tmp_path) -> None:
    repository = JsonPlayerRepository(storage_path=tmp_path / "players.json")

    result = ride_horse_flow(
        repository=repository,
        user_id=950,
        guild_id=951,
        display_name="Mia",
    )

    assert result.player is None
    assert result.has_adopted_horse is False
    assert result.outcome is None
    assert result.ride_stat is None
    assert result.ride_stat_gain == 0
    assert result.energy_loss == 0
    assert result.health_loss == 0
    assert "There is no horse to ride yet" in result.message
    assert "/start" in result.message


def test_ride_horse_flow_stat_gain_and_energy_loss_no_health_loss(tmp_path) -> None:
    """Confidence increases, energy drops by 3d10, health unaffected (skill check passes)."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=952, guild_id=953)
    repository.update_horse_state(
        user_id=952,
        guild_id=953,
        updates={"confidence": 20, "bond": 30, "skill": 50, "energy": 60, "health": 70},
    )

    # d100[0]=90 > confidence(20) → gain; d10[0]=5 → gain=5
    # d10[1]=4, d10[2]=3, d10[3]=2 → energy_loss=9
    # d100[1]=30 <= skill(50) → no health loss
    d100_iter = iter([90, 30])
    d10_iter = iter([5, 4, 3, 2])

    result = ride_horse_flow(
        repository=repository,
        user_id=952,
        guild_id=953,
        display_name="Mia",
        stat_selector=lambda: "confidence",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(42),
    )

    assert result.has_adopted_horse is True
    assert result.ride_stat == "confidence"
    assert result.ride_stat_gain == 5
    assert result.energy_loss == 9
    assert result.health_loss == 0
    assert result.outcome is not None

    # Message contains outcome narrative and stat summary.
    assert "-9 energy" in result.message
    assert "+5 confidence" in result.message
    assert "/horse" in result.message

    persisted = repository.get_player(user_id=952, guild_id=953)
    assert persisted is not None
    assert persisted["horse"]["confidence"] == 25
    assert persisted["horse"]["energy"] == 51
    assert persisted["horse"]["health"] == 70
    assert persisted["horse"]["last_rode_at"] is not None
    assert persisted["horse"]["recent_activity"] is not None


def test_ride_horse_flow_no_stat_gain_with_health_loss(tmp_path) -> None:
    """Bond check fails (no gain), energy drops, health drops due to low skill."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=954, guild_id=955)
    repository.update_horse_state(
        user_id=954,
        guild_id=955,
        updates={"confidence": 20, "bond": 30, "skill": 10, "energy": 60, "health": 70},
    )

    # d100[0]=5 <= bond(30) → no gain, no d10 consumed for gain
    # d10[0]=4, d10[1]=3, d10[2]=2 → energy_loss=9
    # d100[1]=90 > skill(10) → health loss; d10[3]=7
    d100_iter = iter([5, 90])
    d10_iter = iter([4, 3, 2, 7])

    result = ride_horse_flow(
        repository=repository,
        user_id=954,
        guild_id=955,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(42),
    )

    assert result.has_adopted_horse is True
    assert result.ride_stat == "bond"
    assert result.ride_stat_gain == 0
    assert result.energy_loss == 9
    assert result.health_loss == 7

    assert "-9 energy" in result.message
    assert "-7 health" in result.message
    assert "+0" not in result.message

    persisted = repository.get_player(user_id=954, guild_id=955)
    assert persisted is not None
    assert persisted["horse"]["bond"] == 30
    assert persisted["horse"]["energy"] == 51
    assert persisted["horse"]["health"] == 63
    assert persisted["horse"]["last_rode_at"] is not None


def test_ride_horse_flow_energy_clamped_to_zero(tmp_path) -> None:
    """Energy loss exceeding current energy clamps to 0."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=956, guild_id=957)
    repository.update_horse_state(
        user_id=956,
        guild_id=957,
        updates={"confidence": 20, "bond": 30, "skill": 80, "energy": 5, "health": 60},
    )

    # d100[0]=5 <= confidence(20) → no gain
    # d10[0]=10, d10[1]=10, d10[2]=10 → energy_loss=30
    # d100[1]=50 <= skill(80) → no health loss
    d100_iter = iter([5, 50])
    d10_iter = iter([10, 10, 10])

    result = ride_horse_flow(
        repository=repository,
        user_id=956,
        guild_id=957,
        display_name="Mia",
        stat_selector=lambda: "confidence",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(1),
    )

    assert result.energy_loss == 30
    persisted = repository.get_player(user_id=956, guild_id=957)
    assert persisted is not None
    assert persisted["horse"]["energy"] == 0


def test_ride_horse_flow_bond_can_increase(tmp_path) -> None:
    """Bond is the selected stat and increases successfully."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=958, guild_id=959)
    repository.update_horse_state(
        user_id=958,
        guild_id=959,
        updates={"confidence": 50, "bond": 10, "skill": 80, "energy": 70, "health": 80},
    )

    # d100[0]=95 > bond(10) → gain; d10[0]=8
    # d10[1]=3, d10[2]=2, d10[3]=1 → energy_loss=6
    # d100[1]=40 <= skill(80) → no health loss
    d100_iter = iter([95, 40])
    d10_iter = iter([8, 3, 2, 1])

    result = ride_horse_flow(
        repository=repository,
        user_id=958,
        guild_id=959,
        display_name="Mia",
        stat_selector=lambda: "bond",
        d100_roll=lambda: next(d100_iter),
        d10_roll=lambda: next(d10_iter),
        rng=random.Random(7),
    )

    assert result.ride_stat == "bond"
    assert result.ride_stat_gain == 8
    assert result.energy_loss == 6

    persisted = repository.get_player(user_id=958, guild_id=959)
    assert persisted is not None
    assert persisted["horse"]["bond"] == 18
    assert persisted["horse"]["energy"] == 64


def test_ride_horse_flow_recent_activity_is_outcome_text(tmp_path) -> None:
    """recent_activity stored in horse matches the ride outcome's recent_activity_text."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=960, guild_id=961)
    repository.update_horse_state(
        user_id=960,
        guild_id=961,
        updates={"confidence": 80, "bond": 80, "skill": 80, "energy": 90, "health": 90},
    )

    result = ride_horse_flow(
        repository=repository,
        user_id=960,
        guild_id=961,
        display_name="Mia",
        rng=random.Random(123),
    )

    assert result.outcome is not None
    persisted = repository.get_player(user_id=960, guild_id=961)
    assert persisted is not None
    assert persisted["horse"]["recent_activity"] == result.outcome.recent_activity_text


def test_ride_horse_flow_horse_profile_shows_ride_recent_activity(tmp_path) -> None:
    """After /ride, /horse profile shows the ride's recent activity snippet."""
    repository = _make_adopted_repo_for_riding(tmp_path, user_id=962, guild_id=963)
    repository.update_horse_state(
        user_id=962,
        guild_id=963,
        updates={"confidence": 50, "bond": 50, "skill": 50, "energy": 70, "health": 70},
    )

    ride_result = ride_horse_flow(
        repository=repository,
        user_id=962,
        guild_id=963,
        display_name="Mia",
        rng=random.Random(99),
    )

    profile_result = horse_profile_flow(
        repository=repository,
        user_id=962,
        guild_id=963,
        display_name="Mia",
    )

    assert ride_result.outcome is not None
    # The recent activity from the ride should appear in the horse profile.
    assert ride_result.outcome.recent_activity_text in profile_result.message


