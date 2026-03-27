# Refactor Handoff Plan (Dev Branch)

## Current Snapshot
- Branch: `dev`
- Current `HEAD`: `e757c3a`
- Working tree status now:
  - modified: `src/pferdehof_bot/cogs/core.py`
  - modified: `src/pferdehof_bot/services/progression.py`
  - modified: `REFACTOR-HANDOFF-PLAN.md`
- Active shown problems now:
  - none (latest diagnostics check clean).

## Objectives For This Run
1. Start implementation now with small, safe increments.
2. Run tests frequently (targeted while editing, full suite before every commit).
3. Remove all shown problems.
4. Commit all completed changes to `dev`.
5. Keep this file as a live tracker and update after each phase.

## Implementation Phases

### Phase 1: Baseline + diagnostics cleanup
- Scope:
  - fix active typing problem in `src/pferdehof_bot/bot.py`.
  - validate with full pytest.
  - commit on `dev`.
- Status: **completed**
- Completion details:
  - Commit: `a6a4233` (`fix(bot): resolve intents typing diagnostic and start refactor tracker`)
  - Verification: full pytest passed (`166 passed`).

### Phase 2: Shared transport extraction from core cog
- Scope:
  - extract response rendering and interaction context helpers.
  - keep command behavior unchanged.
- Status: **completed (ready to commit)**
- Completed in workspace:
  - Added `src/pferdehof_bot/cogs/shared/context.py`.
  - Added `src/pferdehof_bot/cogs/shared/responder.py`.
  - Added `src/pferdehof_bot/cogs/shared/__init__.py`.
  - Updated `src/pferdehof_bot/cogs/core.py` to delegate context/response logic to shared helpers.
- Verification:
  - diagnostics: clean for edited files.
  - targeted tests: `37 passed`.
  - full suite: `166 passed`.

### Phase 3: View factory extraction
- Scope:
  - extract inline `discord.ui.View` classes from `core.py`.
  - centralize owner-guard/dispatch logic.
- Status: pending

### Phase 4: Readiness policy extraction
- Scope:
  - move train/ride readiness checks out of cog and into service-layer policy helpers.
- Status: **completed (ready to commit)**
- Completed in workspace:
  - Added `can_train_player` and `can_ride_player` to `src/pferdehof_bot/services/progression.py`.
  - Updated `src/pferdehof_bot/cogs/core.py` readiness methods to delegate to progression helpers.
- Verification:
  - diagnostics: clean for edited files.
  - targeted tests: `47 passed`.
  - full suite: `166 passed`.

### Phase 5: Multi-cog split
- Scope:
  - split `core.py` into onboarding/care/progression/stable cogs.
  - update extension loading safely.
- Status: pending

### Phase 6: DI consolidation and hardening
- Scope:
  - inject shared dependencies at composition root.
  - full regression verification.
- Status: pending

## Test Cadence (Mandatory)
1. Run targeted tests after each focused edit cluster.
2. Run full suite before each commit:
   - `d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q`
3. Do not advance phase with failing tests.

## Commit Cadence
1. One commit per completed phase.
2. Conventional, descriptive commit messages.
3. Push `dev` after each completed phase commit.

## Live Progress Log
- 2026-03-28: Phase 1 started.
- 2026-03-28: Removed `intents.message_content = False` in `src/pferdehof_bot/bot.py` to resolve static typing issue while preserving runtime behavior (`Intents.default()` already leaves message content intent disabled).
- 2026-03-28: Diagnostics check clean and full pytest passed (`166 passed`) for Phase 1.
- 2026-03-28: Committed and pushed Phase 1 as `a6a4233` on `dev`.
- 2026-03-28: Extracted shared transport helpers (`context.py`, `responder.py`) and wired `core.py` to use them.
- 2026-03-28: Post-extraction validation complete: targeted (`37 passed`) and full suite (`166 passed`) green.
- 2026-03-28: Committed and pushed Phase 2 as `e757c3a` on `dev`.
- 2026-03-28: Extracted readiness policy helpers into progression service and switched `core.py` to delegate.
- 2026-03-28: Readiness extraction validation complete: targeted (`47 passed`) and full suite (`166 passed`) green.

## Next Actions
1. Commit and push Phase 4 readiness extraction changes.
2. Start Phase 3 by extracting inline view classes from `core.py` into view modules.
3. Run targeted tests after each view family migration, then full pytest before each commit.
