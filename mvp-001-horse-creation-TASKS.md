# MVP-001 Horse Creation - Implementation Tasks

This file is the execution backlog for MVP-001. Work on exactly one task per Copilot session and do not start the next task until the current task is fully done.

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
| T01 | Command contract and UX copy spec | Done | Copilot | 2026-03-22 | README command/failure copy completed; modular Python scaffold created. |
| T02 | Data model and persistence layer | Done | Copilot | 2026-03-22 | Added JSON repository with schema versioning, onboarding/adoption transitions, and persistence tests. Next session start: implement T03 in `src/pferdehof_bot/services/`. |
| T03 | Candidate generation engine (3 horses) | Not Started |  |  |  |
| T04 | `/start` onboarding flow | Not Started |  |  |  |
| T05 | Candidate viewing command (`/horse view`) | Not Started |  |  |  |
| T06 | Candidate selection command (`/horse choose <id>`) | Not Started |  |  |  |
| T07 | Naming command (`/horse name <name>`) with validation | Not Started |  |  |  |
| T08 | Horse profile command (`/horse`) | Not Started |  |  |  |
| T09 | Post-adoption hook command (`/greet` or `/feed`) | Not Started |  |  |  |
| T10 | Telemetry and funnel instrumentation | Not Started |  |  |  |
| T11 | Safety and moderation (profanity + admin override) | Not Started |  |  |  |
| T12 | Integration tests and MVP exit validation | Not Started |  |  |  |

---

## Session History

| Date | Session | Task ID | Summary of Changes | Tests Run | Result |
|---|---|---|---|---|---|
| 2026-03-22 | S01 | T01 | Added full command contract + UX copy to README; created modular package layout and baseline tests. Next session start: implement T02 in `src/pferdehof_bot/repositories/`. | `python -m pytest -q` | Pass (4 passed) |
| 2026-03-22 | S02 | T02 | Implemented JSON-backed player persistence with schema version, CRUD/upsert, onboarding start, candidate choice, horse finalize flow, and adoption conflict guards in `src/pferdehof_bot/repositories/player_repository.py`; added repository unit tests for CRUD and restart persistence. Next session start: implement T03 in `src/pferdehof_bot/services/`. | `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q` | Pass (6 passed) |

---

## Task Details

### T01 - Command contract and UX copy spec
Goal: Define exact slash-command surface and response copy before coding behavior.

Implementation details:
- Add or update a spec section in `README.md` with command signatures:
  - `/start`
  - `/horse view`
  - `/horse choose <id>` where id is `A`, `B`, or `C`
  - `/horse name <name>`
  - `/horse`
  - `/greet` or `/feed`
- Document all error states and expected messages:
  - Already adopted
  - No active onboarding session
  - Invalid candidate id
  - Naming validation failure
- Define tone: cozy, celebratory, personal.

Acceptance criteria:
- Every command has argument rules and one success example.
- Every command has at least one failure example.
- Rules for irreversible choice and one-horse-only are explicit.

Test checklist:
- No code tests required if this task is docs-only.

---

### T02 - Data model and persistence layer
Goal: Persist one horse per player and onboarding state across restarts.

Implementation details:
- Introduce storage module (for MVP, JSON or SQLite).
- Define player record fields:
  - `user_id`
  - `guild_id` (if guild-scoped)
  - `adopted` (bool)
  - `onboarding_session`:
    - `active` (bool)
    - `candidates` (3 generated entries)
    - `chosen_candidate_id` (nullable)
    - `created_at`
  - `horse`:
    - `template_seed`
    - `appearance`
    - `traits_visible`
    - `hint`
    - `name`
    - `created_at`
- Implement repository methods:
  - `get_player(user_id, guild_id)`
  - `upsert_player(record)`
  - `start_onboarding(...)`
  - `set_chosen_candidate(...)`
  - `finalize_horse_name(...)`
- Add migration/version field in persisted format.

Acceptance criteria:
- Data survives bot restart.
- Player cannot hold two adopted horses.
- Schema version exists for forward migration.

Test checklist:
- Unit tests for repository CRUD.
- Unit tests for restart persistence read/write.

---

### T03 - Candidate generation engine (3 horses)
Goal: Generate exactly 3 candidate horses per onboarding session.

Implementation details:
- Create generator module with deterministic seed support.
- Candidate fields:
  - `id` in `A/B/C`
  - `appearance_text` (coat + marking)
  - `hint` (single strength)
  - internal hidden fields for future expansion
- Build weighted pools for:
  - coat colors
  - markings
  - hint strengths
- Ensure no duplicate `id` and avoid fully identical text triplets if possible.

Acceptance criteria:
- Exactly three candidates returned every time.
- Same seed reproduces same candidates.
- Output format is ready for command display.

Test checklist:
- Unit tests for count and id set.
- Unit tests for deterministic output with fixed seed.

---

### T04 - `/start` onboarding flow
Goal: Start onboarding and present horse adoption journey entry point.

Implementation details:
- If player already adopted: return friendly "already have a horse" message.
- If no adoption:
  - create onboarding session
  - generate/store 3 candidates
  - send summary message prompting `/horse view`
- If onboarding session already active, reuse it (no regeneration unless explicitly reset).

Acceptance criteria:
- New players always get onboarding session.
- Existing adopters never enter onboarding again.
- Re-running `/start` is idempotent and safe.

Test checklist:
- Unit tests for new player path.
- Unit tests for adopted-player guard.
- Unit tests for idempotent repeated `/start`.

---

### T05 - Candidate viewing command (`/horse view`)
Goal: Let players inspect the 3 candidates before choosing.

Implementation details:
- Require active onboarding session and no finalized horse.
- Render candidate list with clear labels `A`, `B`, `C`.
- Display lightweight profile for each:
  - appearance text
  - one hint
- End message with instruction to choose: `/horse choose <id>`.

Acceptance criteria:
- Command fails gracefully without active session.
- Candidate output is readable and unambiguous.

Test checklist:
- Unit tests for no-session error.
- Unit tests for successful render payload creation.

---

### T06 - Candidate selection command (`/horse choose <id>`)
Goal: Lock player choice to one of the 3 candidates.

Implementation details:
- Validate id is exactly `A/B/C`.
- Validate onboarding is active.
- Lock chosen candidate in session.
- Make choice irreversible in MVP:
  - if `chosen_candidate_id` already set, return refusal message.
- Prompt naming step: `/horse name <name>`.

Acceptance criteria:
- Invalid ids are rejected with guidance.
- Second choice attempts are blocked.
- Selected candidate is persisted.

Test checklist:
- Unit tests for valid selection path.
- Unit tests for invalid id.
- Unit tests for irreversible lock behavior.

---

### T07 - Naming command (`/horse name <name>`) with validation
Goal: Finalize adoption by assigning valid horse name.

Implementation details:
- Preconditions:
  - active onboarding
  - chosen candidate exists
  - no finalized horse
- Validation rules:
  - length 2-20
  - basic blocklist profanity filter
  - trim leading/trailing spaces
- On success:
  - create finalized horse from chosen candidate
  - set `adopted = true`
  - close onboarding session
  - send celebratory confirmation with horse name and identity summary

Acceptance criteria:
- Invalid names rejected with clear reason.
- Valid name finalizes exactly one horse.
- Re-running naming after adoption is blocked.

Test checklist:
- Unit tests for name length boundaries.
- Unit tests for profanity rejection.
- Unit tests for full finalize transition.

---

### T08 - Horse profile command (`/horse`)
Goal: Show player horse identity post-adoption.

Implementation details:
- If no adopted horse: instruct user to run `/start`.
- If adopted:
  - show name
  - show appearance
  - show 1-2 visible traits
  - show baseline mood/energy text
- Keep numbers hidden in MVP (flavor text only).

Acceptance criteria:
- Correct profile appears for adopters.
- Non-adopters receive actionable guidance.

Test checklist:
- Unit tests for adopter and non-adopter branches.

---

### T09 - Post-adoption hook command (`/greet` or `/feed`)
Goal: Ensure adoption leads directly into at least one interaction loop.

Implementation details:
- Implement one command (`/greet` preferred for simplicity).
- Require adopted horse.
- Return lightweight personalized response referencing horse name.
- Optionally write a simple timestamp for first interaction telemetry.

Acceptance criteria:
- Command works only after adoption.
- Response includes horse name and positive feedback.

Test checklist:
- Unit tests for adoption guard.
- Unit tests for personalized response.

---

### T10 - Telemetry and funnel instrumentation
Goal: Track onboarding funnel and retention leading indicators.

Implementation details:
- Implement event logging function (file or structured logger).
- Emit events:
  - `start_onboarding`
  - `viewed_candidates`
  - `chose_candidate`
  - `named_horse`
  - `first_interaction`
- Include dimensions:
  - `user_id`
  - `guild_id`
  - timestamp
  - candidate id when applicable
- Add minimal query script or instructions for deriving funnel rates.

Acceptance criteria:
- All required events emitted at correct points.
- Event payload shape documented.

Test checklist:
- Unit tests for event emission hooks.
- Unit tests for payload keys.

---

### T11 - Safety and moderation (profanity + admin override)
Goal: Add basic naming safety and a practical override path.

Implementation details:
- Centralize blocklist and name sanitizer.
- Add admin-only command for rename override (optional for MVP, but stub contract at minimum).
- Log moderation actions.

Acceptance criteria:
- Profane blocked names never persist.
- Admin override behavior is documented and permission-checked.

Test checklist:
- Unit tests for blocklist matching.
- Unit tests for permission checks.

---

### T12 - Integration tests and MVP exit validation
Goal: Confirm complete flow reliability and readiness for MVP-002.

Implementation details:
- Add integration-style tests covering full happy path:
  - `/start` -> `/horse view` -> `/horse choose A` -> `/horse name Luna` -> `/horse` -> `/greet`
- Add key failure-path tests:
  - choose before start
  - name before choose
  - second adoption attempt
- Add MVP exit checklist section to `README.md` and mark pass/fail with evidence.

Acceptance criteria:
- Happy path passes reliably.
- Core failure paths are covered.
- Exit checklist completed with current status.

Test checklist:
- Run full test suite and record results in Session History.

---

## Definition of Done (Per Task)

A task may be marked `Done` only if all are true:
- Code and/or docs changes are complete for scope.
- Acceptance criteria in this file are satisfied.
- Required unit/integration tests pass locally.
- Progress Board row is updated.
- Session History row is added.

## Ready-For-Next-Session Checklist

Before ending a session:
- Current task status is updated.
- Any blockers are written in Notes.
- Next session start command is obvious (what to run first, what file to open).
