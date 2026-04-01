#!/usr/bin/env python3
"""Validate all story pack JSON files in the stories/ folder.

Run from the project root:
    python scripts/validate_stories.py

Exit code 0: all files valid.
Exit code 1: one or more errors found.
"""

from __future__ import annotations

import json
import string
import sys
from pathlib import Path

STORIES_FOLDER = Path("stories")

# Must match the rules in playdate_story_engine.py _PLACEHOLDER_RULES.
_STORY_LINE_ALLOWED = frozenset({"initiator_horse", "target_horse", "initiator_player", "target_player"})
_CAMEO_LINE_ALLOWED = frozenset({"initiator_player", "target_player", "one_player"})
_FIELD_RULES: dict[str, frozenset[str]] = {
    "opening_lines": _STORY_LINE_ALLOWED,
    "event_lines": _STORY_LINE_ALLOWED,
    "ending_lines": _STORY_LINE_ALLOWED,
    "cameo_none_lines": _CAMEO_LINE_ALLOWED,
    "cameo_one_lines": _CAMEO_LINE_ALLOWED,
    "cameo_both_lines": _CAMEO_LINE_ALLOWED,
}
_REQUIRED_FIELDS = {"story_id", "tone", "title"} | set(_FIELD_RULES.keys())
_VALID_TONES = {"funny", "cozy", "chaos-lite"}


def _check_entry(entry: object) -> list[str]:
    """Return a list of human-readable error strings for one story entry."""
    if not isinstance(entry, dict):
        return ["Entry must be a JSON object, not a list or primitive."]

    errors: list[str] = []

    # Missing required fields
    missing = _REQUIRED_FIELDS - entry.keys()
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")
        return errors  # Cannot meaningfully validate content without them

    # Tone values
    tone = entry.get("tone")
    if tone not in _VALID_TONES:
        errors.append(f"Unknown tone '{tone}'. Valid values: {sorted(_VALID_TONES)}")

    # Weight sanity
    weight = entry.get("weight")
    if weight is not None and (not isinstance(weight, int) or weight < 1):
        errors.append(f"'weight' must be a positive integer, got: {weight!r}")

    # Line fields: non-empty and placeholder-clean
    for field, allowed in _FIELD_RULES.items():
        lines = entry.get(field)
        if not isinstance(lines, list) or len(lines) == 0:
            errors.append(f"'{field}' must be a non-empty list of strings.")
            continue
        for i, line in enumerate(lines):
            if not isinstance(line, str):
                errors.append(f"'{field}[{i}]' must be a string, got {type(line).__name__!r}.")
                continue
            try:
                placeholders = {
                    fname
                    for _, fname, _, _ in string.Formatter().parse(line)
                    if fname is not None
                }
            except (ValueError, KeyError) as exc:
                errors.append(f"'{field}[{i}]' has invalid format syntax: {exc}")
                continue
            illegal = placeholders - allowed
            if illegal:
                illegal_str = ", ".join(f"{{{p}}}" for p in sorted(illegal))
                allowed_str = ", ".join(f"{{{p}}}" for p in sorted(allowed))
                errors.append(
                    f"'{field}[{i}]': illegal placeholder(s) {illegal_str}. "
                    f"Allowed in this field: {allowed_str}"
                )

    return errors


def _validate_file(json_file: Path) -> tuple[int, list[str]]:
    """Return (valid_story_count, list_of_error_lines) for one JSON file."""
    try:
        with json_file.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return 0, [f"  JSON parse error: line {exc.lineno}, col {exc.colno}: {exc.msg}"]
    except OSError as exc:
        return 0, [f"  Cannot read file: {exc}"]

    if not isinstance(data, dict) or "stories" not in data:
        return 0, ["  Top-level JSON must be an object with a \"stories\" array."]

    valid_count = 0
    error_lines: list[str] = []
    for i, entry in enumerate(data["stories"]):
        story_id = (
            entry.get("story_id", f"<entry {i}>")
            if isinstance(entry, dict)
            else f"<entry {i}>"
        )
        entry_errors = _check_entry(entry)
        if entry_errors:
            for err in entry_errors:
                error_lines.append(f"  Story '{story_id}': {err}")
        else:
            valid_count += 1

    return valid_count, error_lines


def main() -> int:
    if not STORIES_FOLDER.is_dir():
        print(f"ERROR: No '{STORIES_FOLDER}/' folder found. Run from the project root.")
        return 1

    json_files = sorted(STORIES_FOLDER.glob("*.json"))
    if not json_files:
        print(f"No *.json files found in {STORIES_FOLDER}/.")
        return 0

    total_valid = 0
    files_with_errors = 0

    for json_file in json_files:
        try:
            rel = json_file.relative_to(Path.cwd())
        except ValueError:
            rel = json_file

        valid_count, error_lines = _validate_file(json_file)
        if error_lines:
            files_with_errors += 1
            print(f"FAIL  {rel}")
            for line in error_lines:
                print(line)
        else:
            print(f"OK    {rel}  ({valid_count} story/stories)")
        total_valid += valid_count

    print()
    if files_with_errors == 0:
        print(f"All files valid. {total_valid} story/stories ready.")
        return 0
    else:
        print(
            f"{files_with_errors} file(s) with errors. "
            f"{total_valid} valid story/stories across passing files."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
