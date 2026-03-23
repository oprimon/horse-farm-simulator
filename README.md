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

## MVP-002 T01 Slash Command Contract and Loop UX Copy Spec

Tone guidelines:
- Cozy
- Personal
- Encouraging
- Slightly playful

Loop order guidance:
- Recommended daily flow is `/horse` -> `/feed` or `/groom` -> `/rest` if needed -> `/train` -> `/ride`.
- Players can run care commands in any order, but training and riding work best after care.
- Keep responses short so players can learn the loop from command feedback, not from a long tutorial.

Global response visibility:
- Personal horse actions default to ephemeral responses: `/horse`, `/feed`, `/groom`, `/rest`, `/train`, `/ride`.
- Shared roster view defaults to channel-visible response: `/stable`.

### `/horse`

Purpose:
- Show the player's adopted horse profile with readable readiness and progress text.

Response visibility:
- Ephemeral.

Argument rules:
- No arguments.

Success example:
- "Luna seems bright and ready today. Bond feels warm, energy is steady, confidence is growing, and your latest memory is a calm lane ride through wildflowers."

Failure example (not adopted yet):
- "You have not adopted a horse yet. Start with `/start`, then choose and name your companion."

Recovery guidance:
- If not adopted, run `/start` and finish the MVP-001 adoption flow first.

### `/feed`

Purpose:
- Improve immediate readiness by helping your horse recover energy and health.

Response visibility:
- Ephemeral.

Argument rules:
- No arguments.
- Requires an adopted horse.

Success example:
- "You offer Luna a warm feed mix and fresh water. Luna eats happily and looks more energized for the day ahead."

Failure example (not adopted yet):
- "There is no horse to feed yet. Start with `/start` to begin adoption."

Failure example (pacing refusal, if active):
- "Luna has just been fed and is still content. Try `/groom`, `/train`, or come back a bit later."

Recovery guidance:
- If pacing blocks feed, pick a different action now and return later.

### `/groom`

Purpose:
- Strengthen bond and calm confidence through care-focused interaction.

Response visibility:
- Ephemeral.

Argument rules:
- No arguments.
- Requires an adopted horse.

Success example:
- "You brush Luna slowly from neck to shoulder. Luna leans in, relaxed, and your bond feels even closer."

Failure example (not adopted yet):
- "You do not have a horse to groom yet. Start your journey with `/start`."

Failure example (pacing refusal, if active):
- "Luna is already freshly groomed and content. Try `/feed`, `/rest`, or `/train` for now."

Recovery guidance:
- If pacing blocks grooming, choose another care command and return later.

### `/rest`

Purpose:
- Recover energy and support health so the horse is ready for training and riding.

Response visibility:
- Ephemeral.

Argument rules:
- No arguments.
- Requires an adopted horse.

Success example:
- "You give Luna a quiet stable break. After resting, Luna looks calmer, healthier, and better prepared to work."

Failure example (not adopted yet):
- "There is no horse to rest yet. Start with `/start` to adopt one."

Failure example (pacing refusal, if active):
- "Luna is already well-rested right now. Try `/train` or `/ride` while this energy lasts."

Recovery guidance:
- If rest is refused, use the available energy for `/train` or `/ride`.

### `/train`

Purpose:
- Convert care into progression by building skill and confidence at an energy cost.

Response visibility:
- Ephemeral.

Argument rules:
- No arguments.
- Requires an adopted horse.
- May enforce readiness checks for minimum energy and safe health.

Success example:
- "You run a focused ground session with Luna. Luna learns quickly today - skill improves and confidence ticks upward."

Failure example (not adopted yet):
- "You need an adopted horse before training. Begin with `/start`."

Failure example (low energy refusal):
- "Luna is too tired to train safely right now. Try `/feed` or `/rest`, then check `/horse` again."

Failure example (poor health refusal):
- "Luna does not feel healthy enough for training today. Use `/rest` and gentle care before trying again."

Failure example (cooldown or pacing refusal, if active):
- "That was a big effort already. Give Luna a short recovery break before another training session."

Recovery guidance:
- Use `/feed` and `/rest` when refused, then retry `/train`.

### `/ride`

Purpose:
- Deliver short, replayable ride stories that reflect current horse state.

Response visibility:
- Ephemeral.

Argument rules:
- No arguments.
- Requires an adopted horse.
- May enforce ride-readiness checks if horse state is unsafe.

Success example:
- "You and Luna head down a sunlit forest path. Luna stays attentive and brave, and the ride ends with a proud, easy canter home."

Failure example (not adopted yet):
- "You do not have a horse to ride yet. Start with `/start` and finish adoption first."

Failure example (ride blocked by unsafe state):
- "Luna is not in a safe state for riding right now. Try `/rest` and `/feed`, then check readiness with `/horse`."

Failure example (cooldown or pacing refusal, if active):
- "Luna has just finished a ride and needs a breather. Spend a moment on care, then try again later."

Recovery guidance:
- If ride is blocked, stabilize with `/feed` and `/rest`, then build readiness with `/train`.

### `/stable`

Purpose:
- Show the current guild's adopted horse roster for social visibility.

Response visibility:
- Channel-visible.

Argument rules:
- No arguments.
- Scoped to the current guild only.

Success example:
- "Current stable roster:\n1) #001 Luna - Mia\n2) #002 Fjord - Noah\n3) #003 Maple - Erin"

Failure example (no horses available):
- "This stable is still quiet. No horses have been adopted in this server yet. Start with `/start` to welcome the first one."

Failure example (non-guild context):
- "`/stable` is available only inside a server where the stable can be shared."

Recovery guidance:
- If empty, encourage players to run `/start` and complete adoption.

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

## MVP-001 T12 Exit Checklist

Status date: 2026-03-22

- [x] Happy path integration flow passes:
   - `/start` -> `/horse view` -> `/horse choose A` -> `/horse name Luna` -> `/horse` -> `/greet`
   - Evidence: `tests/test_mvp001_integration.py::test_mvp001_happy_path_full_onboarding_to_first_interaction`
- [x] Core failure paths are covered:
   - Choose before start
   - Name before choose
   - Second adoption attempt blocked
   - Evidence: remaining tests in `tests/test_mvp001_integration.py`
- [x] Full automated suite passes locally.
   - Evidence command: `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q`
   - Evidence result: 55 passed

MVP-001 conclusion:
- Pass. Horse creation onboarding is implemented, tested, and validated for progression to MVP-002.
