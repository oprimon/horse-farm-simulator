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
- Horse care actions such as feed, groom, and rest
- Training and first ride loop with readable horse state feedback
- Stable roster command per guild to see adopted horses in the server
- Expanded progression state for bond, energy, health, confidence, and skill
- Ride outcome variety based on horse state and recent activity
- Additional telemetry for balancing and retention analysis

## Data and Persistence

- Player data is stored in data/players.json
- Telemetry events are stored in data/telemetry.jsonl

## Project Structure

- main.py: Runtime entry point
- pyproject.toml: Packaging and tooling config
- src/pferdehof_bot/bot.py: Bot factory and extension loading
- src/pferdehof_bot/cogs/core.py: Command handlers
- src/pferdehof_bot/services/: Onboarding and interaction logic
- src/pferdehof_bot/repositories/: Persistence layer
- tests/: Unit and integration tests
