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
| T03 | Horse state model and persistence extension | Not Started | Copilot | 2026-03-23 | Add persistent state for bond, energy, health, confidence, skill, and action timestamps. |
| T04 | State presentation and profile text service | Not Started | Copilot | 2026-03-23 | Centralize status-band text and reusable profile rendering inputs for commands. |
| T05 | Feed command (`/feed`) | Not Started | Copilot | 2026-03-23 | Implement first care action with adopted-horse guard and state effect. |
| T06 | Groom command (`/groom`) | Not Started | Copilot | 2026-03-23 | Implement bonding-focused care action and response copy. |
| T07 | Rest command (`/rest`) and recovery rules | Not Started | Copilot | 2026-03-23 | Implement recovery action and minimal pacing behavior. |
| T08 | Training command (`/train`) and progression rules | Not Started | Copilot | 2026-03-23 | Add skill/confidence progression with energy cost and readable feedback. |
| T09 | Ride outcome engine and content tables | Not Started | Copilot | 2026-03-23 | Build weighted ride outcomes based on horse state with mostly positive early-tone results. |
| T10 | Ride command (`/ride`) and recent-activity persistence | Not Started | Copilot | 2026-03-23 | Wire slash ride command, persist recent result text, and update `/horse` output. |
| T11 | Stable roster command (`/stable`) | Not Started | Copilot | 2026-03-23 | Add slash stable command that lists horse ids, horse names, and owner display names for the guild. |
| T12 | Telemetry and loop instrumentation | Not Started | Copilot | 2026-03-23 | Emit action, ride, and stable view events for funnel and balance analysis. |
| T13 | Integration tests and loop balance validation | Not Started | Copilot | 2026-03-23 | Cover happy path, stable roster path, poor-state guardrails, and repeat-session persistence. |
| T14 | MVP exit validation and backlog handoff | Not Started | Copilot | 2026-03-23 | Add README exit checklist and capture next-step recommendation for MVP-003. |

---

## Session History

| Date | Session | Task ID | Summary of Changes | Tests Run | Result |
|---|---|---|---|---|---|
| 2026-03-23 | 1 | T01 | Added MVP-002 slash-command UX contract in `README.md` for `/feed`, `/groom`, `/rest`, `/train`, `/ride`, `/stable`, and updated `/horse`; documented visibility, loop order, and failure/recovery copy. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q` (58 passed) | Done |
| 2026-03-23 | 2 | T02 | Added centralized command registry (`src/pferdehof_bot/command_registry.py`), migrated player-facing runtime handlers to slash commands, added startup slash sync configuration, updated README slash usage/mapping, and covered slash wiring + sync/config with tests. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q` (to run in this session) | Done |

---

## Task Details

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
- Increase health and or energy according to balancing rules.
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
- Improve bond and optionally confidence or mood.
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
- Restore energy and support health recovery.
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
- Increase skill and sometimes confidence.
- Consume energy.
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