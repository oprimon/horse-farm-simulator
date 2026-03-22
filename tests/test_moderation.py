"""Unit tests for the moderation module (blocklist matching and name validation)."""

from __future__ import annotations

import pytest

from pferdehof_bot.services.moderation import contains_blocked_name_term, validate_horse_name


# ---------------------------------------------------------------------------
# contains_blocked_name_term
# ---------------------------------------------------------------------------


def test_contains_blocked_name_term_detects_exact_blocked_word() -> None:
    assert contains_blocked_name_term("shit") is True


def test_contains_blocked_name_term_detects_blocked_word_in_phrase() -> None:
    assert contains_blocked_name_term("my fuck horse") is True


def test_contains_blocked_name_term_detects_hyphenated_blocked_word() -> None:
    assert contains_blocked_name_term("shit-horse") is True


def test_contains_blocked_name_term_is_case_insensitive() -> None:
    assert contains_blocked_name_term("FUCK") is True


def test_contains_blocked_name_term_allows_clean_single_word() -> None:
    assert contains_blocked_name_term("Luna") is False


def test_contains_blocked_name_term_allows_clean_phrase() -> None:
    assert contains_blocked_name_term("Silver Star") is False


def test_contains_blocked_name_term_allows_alphanumeric_compound() -> None:
    # "myfuck" is one token — no exact match, so it passes
    assert contains_blocked_name_term("myfuck") is False


# ---------------------------------------------------------------------------
# validate_horse_name
# ---------------------------------------------------------------------------


def test_validate_horse_name_returns_none_error_for_valid_name() -> None:
    normalized, error = validate_horse_name("Luna")
    assert normalized == "Luna"
    assert error is None


def test_validate_horse_name_trims_whitespace() -> None:
    normalized, error = validate_horse_name("  Silver  ")
    assert normalized == "Silver"
    assert error is None


def test_validate_horse_name_rejects_name_too_short() -> None:
    normalized, error = validate_horse_name("A")
    assert error == "length"


def test_validate_horse_name_rejects_empty_string() -> None:
    normalized, error = validate_horse_name("")
    assert error == "length"


def test_validate_horse_name_accepts_minimum_length_name() -> None:
    normalized, error = validate_horse_name("Bo")
    assert normalized == "Bo"
    assert error is None


def test_validate_horse_name_accepts_maximum_length_name() -> None:
    name_20_chars = "A" * 20
    normalized, error = validate_horse_name(name_20_chars)
    assert normalized == name_20_chars
    assert error is None


def test_validate_horse_name_rejects_name_too_long() -> None:
    name_21_chars = "A" * 21
    normalized, error = validate_horse_name(name_21_chars)
    assert error == "length"


def test_validate_horse_name_rejects_profane_name() -> None:
    normalized, error = validate_horse_name("fuck")
    assert error == "profanity"


def test_validate_horse_name_rejects_profane_name_in_phrase() -> None:
    normalized, error = validate_horse_name("my shit horse")
    assert error == "profanity"


def test_validate_horse_name_returns_normalized_string_on_profanity_error() -> None:
    normalized, error = validate_horse_name("  fuck  ")
    assert normalized == "fuck"
    assert error == "profanity"
