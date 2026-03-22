"""Profanity filtering and name sanitization for horse naming safety."""

from __future__ import annotations

import logging
import re

_logger = logging.getLogger(__name__)

BLOCKED_NAME_TERMS: frozenset[str] = frozenset(
    {
        "anal",
        "asshole",
        "bitch",
        "bastard",
        "cock",
        "cunt",
        "dick",
        "fuck",
        "motherfucker",
        "nigger",
        "pussy",
        "shit",
        "slut",
        "whore",
    }
)


def contains_blocked_name_term(name: str) -> bool:
    """Return True when any word token in *name* matches a blocked term."""
    tokens = [token for token in re.split(r"[^a-z0-9]+", name.lower()) if token]
    return any(token in BLOCKED_NAME_TERMS for token in tokens)


def validate_horse_name(name: str) -> tuple[str, str | None]:
    """Validate and normalize a horse name candidate.

    Returns ``(normalized_name, error_reason)`` where *error_reason* is ``None``
    on success, ``"length"`` when the name is too short/long, or ``"profanity"``
    when a blocked term is detected.
    """
    normalized = name.strip()
    if len(normalized) < 2 or len(normalized) > 20:
        return normalized, "length"
    if contains_blocked_name_term(normalized):
        _logger.warning("Blocked horse name attempt detected (length=%d).", len(normalized))
        return normalized, "profanity"
    return normalized, None
