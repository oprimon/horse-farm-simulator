# Pferdehof Sim Discord Bot

Pferdehof Sim is a cozy Discord bot where players adopt a horse and build a personal connection through short, text-first interactions.

## What This Project Is About

This project focuses on lightweight horse companionship inside Discord:
- Start an adoption journey
- View and choose from generated horse candidates
- Name your horse
- Check your horse profile anytime
- Greet your horse for small personalized moments

Design goals:
- Short command flow that fits busy Discord channels
- Friendly, warm tone
- Persistent player progress stored locally

## Setup

### Requirements

- Python 3.12
- A Discord bot token

### Installation

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -e .
```

### Configure Token

Set the DISCORD_TOKEN environment variable before running the bot.

PowerShell example:

```powershell
$env:DISCORD_TOKEN="your-token-here"
```

Optional slash sync controls:

- `DISCORD_COMMAND_SYNC=auto|off|guild|global`
- `DISCORD_DEV_GUILD_ID=<numeric_guild_id>` (required when `DISCORD_COMMAND_SYNC=guild`)

Recommended rollout:

- Default: `DISCORD_COMMAND_SYNC=global` to publish globally-defined commands at startup.
- Development: `DISCORD_COMMAND_SYNC=guild` with a test guild id for fast updates.
- Production: `DISCORD_COMMAND_SYNC=off` after commands are already registered.
- One-time global publish: `DISCORD_COMMAND_SYNC=global` only when intentionally updating global commands.

### Run the Bot

```bash
python main.py
```

## Commands

The bot uses slash commands.

### /start

Starts or resumes horse adoption onboarding.

Example:

```text
/start
```

### /horse profile

Shows your current horse profile (if adopted).

Example:

```text
/horse profile
```

### /horse view

Shows your current candidate horses during onboarding. Each candidate is displayed in a rich embed with a button panel so you can adopt directly without typing an id.

Example:

```text
/horse view
```

After the embed appears, click **Adopt A**, **Adopt B**, or **Adopt C** to lock in your choice. The buttons disable automatically once you choose or after the panel expires (5 minutes).

If the panel has expired or you prefer the command approach, use the slash fallback:

### /horse choose <id>

Locks in a candidate horse by id. Use this as a fallback whenever the button panel from `/horse view` is no longer available.

Rules:
- id must be A, B, or C

Example:

```text
/horse choose B
```

### /horse name <name>

Finalizes adoption by naming your chosen horse.

Rules:
- name is required
- accepted length is 2 to 20 characters after trimming

Example:

```text
/horse name Luna
```

### /horse rename <target_user_id> <new_name>

Admin-only command to rename another player's adopted horse.

Rules:
- requires Discord administrator permission
- target_user_id must be a valid numeric Discord user id

Example:

```text
/horse rename 123456789012345678 Maple
```

### /greet

Sends a short interaction response with your adopted horse.

Example:

```text
/greet
```

Migration mapping from prefix to slash:

- `!start` -> `/start`
- `!horse` -> `/horse profile`
- `!horse view` -> `/horse view`
- `!horse choose` -> `/horse choose`
- `!horse name` -> `/horse name`
- `!horse rename` -> `/horse rename`
- `!greet` -> `/greet`

## MVP-002 Exit Checklist

Status date: 2026-03-25

1. PASS: Adopted players can use care commands, train, and ride reliably.
Evidence: Slash commands `/feed`, `/groom`, `/rest`, `/train`, and `/ride` are implemented with adopter/readiness guardrails (including `/ride` requiring at least 30 energy and 10 health) and covered by integration tests in `tests/test_mvp002_integration.py`.
2. PASS: Horse state changes persist across restarts.
Evidence: Horse state persistence and migration behavior are implemented in the repository layer and verified by repository and integration tests, including reload coverage in `tests/test_mvp002_integration.py`.
3. PASS: Ride outcomes visibly reflect horse state.
Evidence: Weighted ride outcomes are produced by `src/pferdehof_bot/services/ride_outcomes.py` and consumed by ride flow logic with deterministic branch coverage in `tests/test_ride_outcomes.py` and onboarding service tests.
4. PASS: Telemetry captures enough data to measure loop completion and repeat usage.
Evidence: MVP-002 loop events (`fed_horse`, `groomed_horse`, `rested_horse`, `trained_horse`, `rode_horse`, `ride_outcome`, `viewed_stable`) are emitted and validated in `tests/test_telemetry.py`; analysis command is documented in this README.
5. PASS: The resulting loop is strong enough to justify MVP-003.
Evidence: Full MVP-002 feature slice (care, train, ride, stable, persistence, and telemetry) is complete and validated by the full pytest suite recorded in the task history.

## MVP-003 Handoff Recommendation

Recommendation: MVP-003 should prioritize shared stable memories and light cooperative stable interactions before expanding complexity (economy, breeding, or deep admin tooling).

Reasoning:
- MVP-002 already validates the solo attachment loop and state progression.
- Telemetry now supports measuring whether social features improve multi-day retention.
- Memory and cooperative moments are a natural extension of the cozy tone without increasing system burden too early.

Next session start command (MVP-003 planning):

```bash
d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q
```

Then open `mvp-002-care-training-first-ride.md` and draft the MVP-003 planning note focused on shared memories and cooperative stable interactions.

## Data and Persistence

- Player data is stored in data/players.json
- Telemetry events are stored in data/telemetry.jsonl

### Telemetry Event Contract (MVP-002)

The bot emits JSON Lines telemetry events for onboarding and loop instrumentation.

Supported event names:

- start_onboarding
- viewed_candidates
- chose_candidate
- named_horse
- first_interaction
- fed_horse
- groomed_horse
- rested_horse
- trained_horse
- rode_horse
- ride_outcome
- viewed_stable

Payload fields:

- event_name (required)
- user_id (required)
- guild_id (required when in a guild, otherwise null)
- timestamp (required, UTC ISO-8601)
- candidate_id (on candidate selection/naming events)
- horse_name (on care, training, and ride events)
- outcome_id (on ride_outcome)
- outcome_category (on ride_outcome)

Sample event payloads:

```json
{"event_name":"fed_horse","user_id":123,"guild_id":456,"timestamp":"2026-03-25T08:42:13.000000+00:00","horse_name":"Maple"}
{"event_name":"ride_outcome","user_id":123,"guild_id":456,"timestamp":"2026-03-25T09:01:22.000000+00:00","horse_name":"Maple","outcome_id":"steady_trot","outcome_category":"good"}
```

Analysis instructions:

- Funnel conversion summary (onboarding): `python scripts/summarize_telemetry.py data/telemetry.jsonl`
- Keep telemetry for analysis only (no gameplay decisions depend on telemetry delivery).
- Check loop usage by counting unique `user_id:guild_id` pairs per event and comparing care -> train -> ride progression.

## Project Structure

- main.py: Runtime entry point
- pyproject.toml: Packaging and tooling config
- src/pferdehof_bot/bot.py: Bot factory and extension loading
- src/pferdehof_bot/cogs/core.py: Command handlers
- src/pferdehof_bot/services/: Domain service layer split by workflow responsibility
- src/pferdehof_bot/repositories/: Persistence layer
- tests/: Unit and integration tests

### Service Architecture

The service layer is intentionally split so each module owns one workflow surface:

- src/pferdehof_bot/services/lifecycle.py: Onboarding lifecycle and profile flows (`/start`, candidate selection, naming, greet, profile, admin rename)
- src/pferdehof_bot/services/care.py: Care loops (`/feed`, `/groom`, `/rest`)
- src/pferdehof_bot/services/progression.py: Training and ride progression (`/train`, `/ride`)
- src/pferdehof_bot/services/stable.py: Guild stable roster flow (`/stable`)
- src/pferdehof_bot/services/presentation_models.py: Shared response presentation dataclasses used by all workflow modules
- src/pferdehof_bot/services/flow_utils.py: Shared helper utilities used across flow modules
- src/pferdehof_bot/services/state_presentation.py: Horse state-to-text mapping helpers for profile and ride summaries
- src/pferdehof_bot/services/telemetry.py: Telemetry payload assembly and logging adapters

`src/pferdehof_bot/services/__init__.py` remains available as a convenience import surface, while internal modules and tests prefer direct imports from concrete service modules.
