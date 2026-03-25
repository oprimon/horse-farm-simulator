# MVP-002 Care, Training, and First Ride - Implementation Tasks

This file is the execution backlog for MVP-002. Work on exactly one task per Copilot session and do not start the next task until the current task is fully done.

## Workflow Rules (One Task Per Session)

1. Move one task from `Not Started` to `In Progress`.
2. Implement only that task.
3. Run tests for changed behavior.
4. Mark task `Done` only if all acceptance criteria are met.
5. Log the session in the session history table.

Status values:
- `Not Started`
- `In Progress`
- `Done`
- `Blocked`

---

## Progress Board

| ID | Task | Status | Owner | Last Updated | Notes |
|---|---|---|---|---|---|
| T01 | Slash-command contract and loop UX copy spec | Done | Copilot | 2026-03-23 | Command contract, visibility rules, success/failure examples, and recovery guidance added to `README.md`. |
| T02 | Slash migration and command registry foundation | Done | Copilot | 2026-03-23 | Migrated `/start`, `/horse` subcommands, and `/greet` to slash commands; added centralized command registry metadata and environment-safe command sync strategy (`off`, `guild`, `global`). Admin rename migrated as `/horse rename`. |
| T03 | Horse state model and persistence extension | Done | Copilot | 2026-03-23 | Added schema v2 horse-state persistence, migration for MVP-001 records, state update repository API, and deterministic guild stable roster query with owner linkage. |
| T04 | State presentation and profile text service | Done | Copilot | 2026-03-23 | Added `state_presentation` service for readable readiness/bond/energy/confidence/skill bands; reused in `/horse` profile rendering with recent-activity text. |
| T05 | Feed command (`/feed`) | Done | Copilot | 2026-03-25 | Added slash `/feed` flow with adopter guard, `1d10` energy gain clamped to `100`, and persisted `last_fed_at` plus `recent_activity`. |
| T06 | Groom command (`/groom`) | Done | Copilot | 2026-03-25 | Added slash `/groom` with adopted-horse guard, chance-based `bond` or `health` increase via `1d100` check and `1d10` delta, and persisted `last_groomed_at` plus `recent_activity`. |
| T07 | Rest command (`/rest`) and recovery rules | Done | Copilot | 2026-03-25 | Added slash `/rest` with adopted-horse guard, `1d10` health gain clamped to `100`, and persisted `last_rested_at` plus `recent_activity`. |
| T08 | Training command (`/train`) and progression rules | Done | Copilot | 2026-03-25 | Added slash `/train` with readiness guards, chance-based skill and confidence gains, `1d10` energy cost, slight skill-based health risk, and readable `/ride` guidance. |
| T09 | Ride outcome engine and content tables | Done | Copilot | 2026-03-25 | Created `ride_outcomes.py` service with 13 content entries across 4 weighted categories (excellent/good/fair/setback); `select_ride_outcome` uses a readiness score (energy×0.30 + confidence×0.30 + bond×0.20 + skill×0.20) for weighted category selection; injectable RNG for deterministic testing; 24 unit tests covering weights, structure, determinism, and edge cases. |
| T10 | Ride command (`/ride`) and recent-activity persistence | Done | Copilot | 2026-03-25 | Added `ride_horse_flow` with adopted-horse guard, chance-based confidence/bond gain (`1d100`/`1d10`), always-apply `3d10` energy loss, chance skill-check health loss; outcome narrative from `ride_outcomes` engine; persisted `last_rode_at` + `recent_activity`; `/horse` profile already shows recent activity via T04 state presentation. |
| T11 | Stable roster command (`/stable`) | Not Started | Copilot | 2026-03-23 | Add slash stable command that lists horse ids, horse names, and owner display names for the guild. |
| T12 | Telemetry and loop instrumentation | Not Started | Copilot | 2026-03-23 | Emit action, ride, and stable view events for funnel and balance analysis. |
| T13 | Integration tests and loop balance validation | Not Started | Copilot | 2026-03-23 | Cover happy path, stable roster path, poor-state guardrails, and repeat-session persistence. |
| T14 | MVP exit validation and backlog handoff | Not Started | Copilot | 2026-03-23 | Add README exit checklist and capture next-step recommendation for MVP-003. |

---

## Session History

| Date | Session | Task ID | Summary of Changes | Tests Run | Result |
|---|---|---|---|---|---|
| 2026-03-23 | 1 | T01 | Added MVP-002 slash-command UX contract in `README.md` for `/feed`, `/groom`, `/rest`, `/train`, `/ride`, `/stable`, and updated `/horse`; documented visibility, loop order, and failure/recovery copy. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q` (58 passed) | Done |
| 2026-03-23 | 2 | T02 | Added centralized command registry (`src/pferdehof_bot/command_registry.py`), migrated player-facing runtime handlers to slash commands, added startup slash sync configuration, updated README slash usage/mapping, and covered slash wiring + sync/config with tests. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q` (69 passed) | Done |
| 2026-03-23 | 3 | T03 | Extended repository to schema v2 with persisted horse progression fields (`horse_id`, bond, energy, health, confidence, skill, action timestamps, and recent activity), added migration-safe normalization for MVP-001 records, introduced `update_horse_state` and deterministic `list_adopted_horses_by_guild` APIs, and added repository migration/roster tests. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/pytest.exe -q` (71 passed) | Done |
| 2026-03-23 | 4 | T04 | Added new state-presentation service with consistent banded copy for readiness, bond, energy, confidence, and skill; integrated it into `/horse` profile output and added unit tests for mapping plus profile payload generation. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/pytest.exe -q` (78 passed) | Done |
| 2026-03-25 | 5 | T05 | Implemented slash `/feed` in `CoreCog`, added `feed_horse_flow` with adopted-horse guard and deterministic `1d10` energy delta handling, persisted `last_fed_at` + `recent_activity`, and extended slash/registry and service tests for feed behavior. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/pytest.exe -q` (80 passed) | Done |
| 2026-03-25 | 6 | T06 | Implemented slash `/groom` in `CoreCog`, added `groom_horse_flow` with adopted-horse guard and chance-based `bond`/`health` progression (`1d100` check, `1d10` gain), persisted `last_groomed_at` + `recent_activity`, and extended slash/registry and onboarding service tests for grooming behavior. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/pytest.exe -q` (83 passed) | Done |
| 2026-03-25 | 7 | T07 | Implemented slash `/rest` in `CoreCog`, added `rest_horse_flow` with adopted-horse guard and always-apply `1d10` health gain (clamped to `100`), persisted `last_rested_at` + `recent_activity`, and added slash/registry and onboarding service tests for rest behavior. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/pytest.exe -q` (87 passed) | Done |
| 2026-03-25 | 8 | T08 | Implemented slash `/train` in `CoreCog`, added `train_horse_flow` with adopted-horse guard, readiness refusal for low energy or health, chance-based skill and confidence progression, `1d10` energy cost, slight skill-based health-loss risk, persisted `last_trained_at` + `recent_activity`, and extended slash/registry and onboarding service tests for training behavior. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/pytest.exe -q` (91 passed) | Done |
| 2026-03-25 | 10 | T10 | Added `RideHorseResult` dataclass and `ride_horse_flow` service in `onboarding.py` with adopted-horse guard, `_chance_to_decrease` helper, `select_ride_outcome` integration, `3d10` energy loss, chance confidence/bond gain, chance skill-check health loss, and `last_rode_at`/`recent_activity` persistence; added `/ride` slash command in `CoreCog`; registered `ride` in `command_registry.py`; exported from `services/__init__.py`; added 8 unit tests (guard, stat gain, health loss, energy clamp, bond increase, recent-activity persistence, profile integration) and updated slash-command registration tests. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q` (122 passed) | Done |

---

## Task Details

### Shared mechanical rules for T05-T10
Apply these rules consistently in implementation and tests:
- All state values clamp to `0..100`.
- `increases`: always add rolled amount; clamp to `100`.
- `decreases`: always subtract rolled amount; clamp to `0`.
- `has a chance to increase`: roll `1d100`; if roll is higher than current checked value, apply the configured increase roll amount (for this MVP baseline, `1d10`).
- `has a chance (<attribute>) to decrease`: roll `1d100` vs `<attribute>`; if roll is higher, decrease target stat by configured roll amount.
- `has a slight chance (<attribute>) to decrease`: roll `1d100` twice vs `<attribute>`; if both rolls are higher, decrease target stat by configured roll amount.
- Consistency rule: `d100` handles checks, `d10` handles stat deltas.

### T01 - Slash-command contract and loop UX copy spec
Goal: Define exact slash-command surface and player-facing copy for the first repeatable care loop before coding behavior.

Implementation details:
- Add or update a spec section in `README.md` with slash command signatures:
  - `/feed`
  - `/groom`
  - `/rest`
  - `/train`
  - `/ride`
  - `/stable`
  - updated `/horse`
- Document command purpose, success examples, and recovery guidance.
- Document all common failure states:
  - no adopted horse
  - low-energy or poor-health training refusal
  - ride blocked by unsafe state, if enforced
  - cooldown or pacing refusal, if enforced
  - no horses available for `/stable`
- Define tone: cozy, personal, encouraging, and slightly playful.

Acceptance criteria:
- Every command has argument rules and one success example.
- Every command has at least one failure example.
- Copy makes the loop order understandable without a tutorial wall.
- Slash command behavior and response visibility (ephemeral or channel) are specified per command.

Test checklist:
- No code tests required if this task is docs-only.

---

### T02 - Slash migration and command registry foundation
Goal: Move the command surface to slash commands and centralize command definitions before adding MVP-002 loop behaviors.

Implementation details:
- Convert existing player-facing commands from prefix to slash command equivalents:
  - `/start`
  - `/horse` (including view, choose, and name behavior)
  - `/greet`
- Define a command registry as the source of truth for command metadata.
- Registry must include at least:
  - command and subcommand identifiers
  - response visibility intent (ephemeral or channel)
  - permission constraints where applicable
- Add startup command sync strategy for development and rollout safety.
- Keep behavior parity for MVP-001 flows while changing command transport.

Implementation order checklist:
1. Add a command registry module and define metadata for existing commands first.
2. Add slash command sync bootstrap at startup with environment-safe behavior.
3. Migrate `/start` to slash and verify onboarding entry behavior parity.
4. Migrate `/horse` slash surface (profile, view, choose, name) and verify full adoption path.
5. Migrate `/greet` and verify adopted-horse guard behavior.
6. Decide admin rename scope for this task and either migrate now or defer with explicit note.
7. Remove or disable old prefix handlers once slash parity tests pass.
8. Update `README.md` command usage examples from prefix to slash commands.
9. Run full pytest suite and record result in Session History.

Acceptance criteria:
- Existing player-facing commands are available as slash commands.
- Command metadata is centralized in one registry structure, not scattered across handlers.
- Runtime startup path includes clear command sync behavior.
- MVP-001 onboarding flow remains functionally equivalent through slash commands.

Test checklist:
- Unit tests for slash command handler wiring and guardrails.
- Integration-style test for core onboarding flow via slash commands.
- Regression tests for admin-only command permission behavior if migrated in scope.

---

### T03 - Horse state model and persistence extension
Goal: Persist the first care and progression state for each adopted horse.

Implementation details:
- Extend persisted horse data with:
  - `horse_id`
  - `bond`
  - `energy`
  - `health`
  - `confidence`
  - `skill`
  - `last_fed_at`
  - `last_groomed_at`
  - `last_rested_at`
  - `last_trained_at`
  - `last_rode_at`
  - `recent_activity`
- Introduce any schema version bump required for migration.
- Add repository methods for loading, updating, and persisting state changes.
- Add repository support for listing adopted horses by guild for stable roster rendering.

Acceptance criteria:
- Horse state survives bot restart.
- Existing adopted-horse records migrate safely.
- Repository API can support all MVP-002 commands without ad hoc dict mutation in command handlers.
- Stable roster queries return deterministic ordering and include owner linkage.

Test checklist:
- Unit tests for persistence read/write.
- Unit tests for migration from MVP-001 records.
- Unit tests for guild stable roster query behavior.

---

### T04 - State presentation and profile text service
Goal: Make hidden state readable through consistent status text instead of raw numbers.

Implementation details:
- Create a service that maps internal state to player-facing bands.
- Define readable text for:
  - mood or readiness
  - bond feel
  - energy feel
  - confidence feel
  - skill progress feel
- Reuse this service in `/horse`, `/train`, and `/ride` responses.

Acceptance criteria:
- Player-facing copy stays consistent across commands.
- `/horse` can describe state without exposing raw numeric internals.

Test checklist:
- Unit tests for state-band mapping.
- Unit tests for representative profile payload generation.

---

### T05 - Feed command (`/feed`)
Goal: Add the first nurturing action that improves readiness and reinforces attachment.

Implementation details:
- Require adopted horse.
- Always increase energy by `1d10` (max `100`).
- Return a short personalized response using horse name.
- Persist timestamp and recent activity summary.

Acceptance criteria:
- Command works only for adopters.
- Feeding changes horse state predictably.
- Response communicates a meaningful result, not generic confirmation.

Test checklist:
- Unit tests for adopted-horse guard.
- Unit tests for state update and response payload.

---

### T06 - Groom command (`/groom`)
Goal: Add a care action that emphasizes bond and calmness.

Implementation details:
- Require adopted horse.
- Apply chance-to-increase logic to either bond or health:
  - choose target stat (bond or health),
  - roll `1d100` against the chosen current value,
  - if roll is higher, increase chosen stat by `1d10` (max `100`).
- Persist timestamp and recent activity summary.
- Keep the result short and cozy.

Acceptance criteria:
- Grooming has a distinct effect from feeding.
- Personalized response references horse identity and reaction.

Test checklist:
- Unit tests for adopted-horse guard.
- Unit tests for grooming-specific state effects.

---

### T07 - Rest command (`/rest`) and recovery rules
Goal: Add the simplest pacing and recovery mechanic so actions feel like part of an ongoing routine.

Implementation details:
- Require adopted horse.
- Always increase health by `1d10` (max `100`).
- Define minimal recovery rules and any soft pacing needed to prevent spam-only optimization.
- Persist timestamp and recent activity summary.

Acceptance criteria:
- Rest provides a clear recovery role in the loop.
- Recovery behavior is simple enough to understand from command responses.

Test checklist:
- Unit tests for adopted-horse guard.
- Unit tests for recovery state changes and pacing behavior.

---

### T08 - Training command (`/train`) and progression rules
Goal: Turn care into visible progression by adding a skill-building step with tradeoffs.

Implementation details:
- Require adopted horse.
- Check readiness preconditions such as minimum energy or health if used.
- Chance to increase skill by `1d10` (max `100`) using `1d100` vs current skill.
- Slight chance (skill check) to decrease health by `1d10` (min `0`) using two `1d100` rolls.
- Persist timestamp and recent activity summary.

Acceptance criteria:
- Training is blocked gracefully when horse state is too poor.
- Successful training creates visible progression and a clear next step toward `/ride`.

Test checklist:
- Unit tests for refusal conditions.
- Unit tests for successful progression updates.

---

### T09 - Ride outcome engine and content tables
Goal: Generate short ride stories that reflect horse state and create replayable moments.

Implementation details:
- Create a ride outcome generator with weighted branching based on state.
- Outcomes should consider at least:
  - energy
  - confidence
  - bond
  - skill
- Build mostly positive early outcomes with gentle setbacks.
- Define resulting state changes and recent-activity text.

Acceptance criteria:
- Ride results feel connected to prior care and training.
- Outcome selection is testable and deterministic where needed.

Test checklist:
- Unit tests for deterministic output with fixed input state.
- Unit tests for outcome weighting or branch selection rules.

---

### T10 - Ride command (`/ride`) and recent-activity persistence
Goal: Deliver the first fun action that pays off the care and training loop.

Implementation details:
- Require adopted horse.
- Validate any ride readiness rules.
- Use the ride outcome engine to generate response text and state changes.
- Apply baseline state changes:
  - chance to increase confidence or bond by `1d10` (max `100`) via `1d100` check against selected stat,
  - always decrease energy by `3d10` (min `0`),
  - chance (skill check) to decrease health by `1d10` (min `0`) via `1d100` vs skill.
- Persist timestamps and recent activity.
- Expand `/horse` to show latest activity or ride memory snippet.
- Implement command as slash command and document response visibility choice.

Acceptance criteria:
- `/ride` works reliably after adoption.
- `/horse` reflects that something meaningful happened recently.

Test checklist:
- Unit tests for ride guardrails.
- Unit tests for successful ride state and persistence updates.
- Unit tests for updated `/horse` output branch.

---

### T11 - Stable roster command (`/stable`)
Goal: Add a social visibility surface that shows the current guild stable at a glance.

Implementation details:
- Implement `/stable` as a slash command.
- List all adopted horses in the current guild.
- For each row include:
  - horse id
  - horse name
  - owner display name
- Define stable sorting rules and empty-state response.
- Ensure command does not expose guild-external player data.

Acceptance criteria:
- `/stable` returns readable, unambiguous roster output.
- Empty guild state is handled gracefully.
- Output includes both horse id and owner identity for each entry.

Test checklist:
- Unit tests for empty roster response.
- Unit tests for multi-player roster rendering and sorting.
- Unit tests for guild scoping behavior.

---

### T12 - Telemetry and loop instrumentation
Goal: Measure whether the new loop is being used and where players drop out.

Implementation details:
- Emit events:
  - `fed_horse`
  - `groomed_horse`
  - `rested_horse`
  - `trained_horse`
  - `rode_horse`
  - `ride_outcome`
  - `viewed_stable`
- Include dimensions:
  - `user_id`
  - `guild_id`
  - timestamp
  - horse name when appropriate
  - outcome id or category for rides
- Document payload shape and analysis instructions.

Acceptance criteria:
- All required events emit at the correct points.
- Payload shape is documented and consistent.

Test checklist:
- Unit tests for event emission hooks.
- Unit tests for payload keys.

---

### T13 - Integration tests and loop balance validation
Goal: Confirm the full care -> train -> ride journey behaves reliably and supports repeat play.

Implementation details:
- Add integration-style tests covering a happy path such as:
  - adopt horse in MVP-001 flow
  - `/feed`
  - `/groom`
  - `/train`
  - `/ride`
  - `/horse`
  - `/stable`
- Add key failure-path tests:
  - command before adoption
  - `/train` with poor state
  - `/ride` when readiness rules are not met, if enforced
  - persisted state after repository reload

Acceptance criteria:
- Happy path passes reliably.
- Core failure paths are covered.
- Persistence across reload is verified for the new state model.
- Stable roster output is verified for correctness and guild scoping.

Test checklist:
- Run focused integration tests.
- Run full test suite and record results in Session History.

---

### T14 - MVP exit validation and backlog handoff
Goal: Confirm readiness for the next expansion after the solo daily loop is working.

Implementation details:
- Add MVP-002 exit checklist section to `README.md`.
- Mark pass or fail with evidence.
- Record whether social memory or cooperative stable features should be MVP-003.

Acceptance criteria:
- Exit checklist is complete and evidence-backed.
- Next session start command is obvious for MVP-003 planning.

Test checklist:
- No new code tests required if this task is docs-only.
- Reference latest full suite result in Session History.

---

## Definition of Done (Per Task)

A task may be marked `Done` only if all are true:
- Code and or docs changes are complete for scope.
- Acceptance criteria in this file are satisfied.
- Required unit or integration tests pass locally.
- Progress Board row is updated.
- Session History row is added.

## Ready-For-Next-Session Checklist

Before ending a session:
- Current task status is updated.
- Any blockers are written in Notes.
- Next session start command is obvious (what to run first, what file to open).