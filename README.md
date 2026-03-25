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

- Default: `DISCORD_COMMAND_SYNC=auto` to sync globally-defined commands to connected guilds at startup for immediate availability.
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

Shows your current candidate horses during onboarding.

Example:

```text
/horse view
```

### /horse choose <id>

Locks in a candidate horse by id.

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

## Planned Features

The following features are planned for upcoming development:
- Integration tests for the full MVP-002 loop and persistence reload paths
- MVP-002 exit checklist and MVP-003 recommendation handoff

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
- src/pferdehof_bot/services/: Onboarding and interaction logic
- src/pferdehof_bot/repositories/: Persistence layer
- tests/: Unit and integration tests
