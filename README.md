# Pferdehof Sim Discord Bot

Pferdehof Sim is a cozy Discord horse-adoption bot built with `discord.py`.

## Getting Started

1. Make sure Python 3.11+ is installed.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```bash
   pip install -e .
   ```

4. Set environment variable `DISCORD_TOKEN`.
5. Run the bot:

   ```bash
   python main.py
   ```

## MVP-001 T01 Command Contract and UX Copy Spec

Tone guidelines:
- Cozy
- Celebratory
- Personal

Global gameplay rules:
- One-horse-only: each player can adopt exactly one horse in MVP-001.
- Irreversible choice: once a candidate is chosen with `/horse choose <id>`, the candidate cannot be changed in MVP-001.

### `/start`

Argument rules:
- No arguments.

Success example:
- "Welcome to Pferdehof, Mia. Three horses are waiting to meet you. Use `/horse view` to see your candidates."

Failure example (already adopted):
- "You already have a horse, Mia. You can visit them with `/horse` and say hello with `/greet`."

### `/horse view`

Argument rules:
- No arguments.
- Requires an active onboarding session.

Success example:
- "Here are your three candidates:\nA) Chestnut coat, white blaze - Hint: unusually calm around new people\nB) Dapple gray, one white sock - Hint: loves trail rhythm\nC) Bay coat, star marking - Hint: learns routines quickly\nChoose with `/horse choose <id>`."

Failure example (no active onboarding session):
- "I cannot show candidates yet. Start your adoption journey with `/start`."

### `/horse choose <id>`

Argument rules:
- `id` must be exactly `A`, `B`, or `C` (case-insensitive input may be normalized).
- Requires an active onboarding session.
- Choice is irreversible once saved.

Success example:
- "Beautiful choice. Candidate B is now your future companion. Next, give your horse a name with `/horse name <name>`."

Failure example (invalid candidate id):
- "I could not find candidate `D`. Please choose `A`, `B`, or `C` using `/horse choose <id>`."

Failure example (already locked choice):
- "Your choice is already locked in for this adoption. In MVP-001, horse choice cannot be changed."

### `/horse name <name>`

Argument rules:
- `name` is required.
- Name is trimmed before validation.
- Length must be 2-20 characters after trimming.
- Basic profanity blocklist must reject unsafe names.
- Requires active onboarding and a previously chosen candidate.

Success example:
- "Meet Luna, your new horse. Luna looks radiant today and already seems to trust your voice."

Failure example (validation failure - too short):
- "That name is too short. Please pick a name between 2 and 20 characters."

Failure example (validation failure - profanity):
- "That name is not allowed here. Please choose a kind and stable-safe name."

Failure example (no chosen candidate yet):
- "Choose your horse first with `/horse choose <id>`, then return to naming."

Failure example (already adopted):
- "Naming is complete. You already adopted your horse. View profile with `/horse`."

### `/horse`

Argument rules:
- No arguments.

Success example:
- "Luna greets you with bright eyes. Appearance: chestnut coat with a white blaze. Traits: calm with newcomers, quick to settle into routines."

Failure example (not adopted yet):
- "You have not adopted a horse yet. Begin with `/start`."

### `/greet`

Argument rules:
- No arguments.
- Requires an adopted horse.

Success example:
- "You greet Luna softly. Luna nudges your shoulder and seems happy to see you."

Failure example (not adopted yet):
- "There is no horse to greet yet. Start your adoption journey with `/start`."

## Project Structure

- `main.py`: Minimal runtime entry point.
- `pyproject.toml`: Packaging and test configuration.
- `src/pferdehof_bot/__init__.py`: Package metadata.
- `src/pferdehof_bot/bot.py`: Discord bot construction and extension loading.
- `src/pferdehof_bot/config.py`: Environment-backed runtime settings.
- `src/pferdehof_bot/cogs/`: Command cogs.
- `src/pferdehof_bot/domain/`: Domain entities and value objects.
- `src/pferdehof_bot/services/`: Business services for onboarding/adoption flow.
- `src/pferdehof_bot/repositories/`: Persistence interfaces and implementations.
- `tests/`: Unit tests.

## Status

T01 (command contract and UX copy) is defined in this README. Implementation tasks begin with T02.

## MVP-001 T10 Telemetry Events

Telemetry storage:
- Structured JSON Lines file at `data/telemetry.jsonl`.

Event payload shape:

```json
{
   "event_name": "chose_candidate",
   "user_id": 123456789,
   "guild_id": 987654321,
   "timestamp": "2026-03-22T18:30:00+00:00",
   "candidate_id": "B"
}
```

Required events:
- `start_onboarding`
- `viewed_candidates`
- `chose_candidate`
- `named_horse`
- `first_interaction`

Field rules:
- `event_name`: funnel milestone identifier.
- `user_id`: Discord user id.
- `guild_id`: Discord guild id, or `null` for non-guild context.
- `timestamp`: ISO 8601 UTC timestamp for event emission.
- `candidate_id`: included for candidate-specific milestones such as `chose_candidate` and `named_horse`.

Funnel summary script:

```bash
python scripts/summarize_telemetry.py data/telemetry.jsonl
```

The script reports unique user counts per funnel step, step-to-step conversion rate, and overall conversion from `start_onboarding`.
