"""Summarize onboarding funnel telemetry from a JSON Lines event log."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys


FUNNEL_STEPS = [
    "start_onboarding",
    "viewed_candidates",
    "chose_candidate",
    "named_horse",
    "first_interaction",
]


def main() -> int:
    telemetry_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data") / "telemetry.jsonl"
    if not telemetry_path.exists():
        print(f"Telemetry file not found: {telemetry_path}")
        return 1

    users_by_event: dict[str, set[str]] = defaultdict(set)
    with telemetry_path.open("r", encoding="utf-8") as telemetry_file:
        for raw_line in telemetry_file:
            stripped = raw_line.strip()
            if not stripped:
                continue
            event = json.loads(stripped)
            event_name = str(event.get("event_name", ""))
            user_id = event.get("user_id")
            guild_id = event.get("guild_id")
            if not event_name or user_id is None:
                continue
            users_by_event[event_name].add(f"{user_id}:{guild_id}")

    start_count = len(users_by_event.get("start_onboarding", set()))
    print(f"Telemetry file: {telemetry_path}")
    for index, step in enumerate(FUNNEL_STEPS, start=1):
        current_count = len(users_by_event.get(step, set()))
        previous_step = FUNNEL_STEPS[index - 2] if index > 1 else None
        previous_count = len(users_by_event.get(previous_step, set())) if previous_step is not None else current_count
        step_rate = (current_count / previous_count * 100.0) if previous_count else 0.0
        overall_rate = (current_count / start_count * 100.0) if start_count else 0.0
        print(
            f"{step}: users={current_count} step_rate={step_rate:.1f}% overall_from_start={overall_rate:.1f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())