# Refactor Handoff Plan (Dev Branch)

## Current Snapshot
- Branch: `dev`
- Current `HEAD`: `49c8411`
- Working tree status at start of this run:
  - modified: `REFACTOR-HANDOFF-PLAN.md`
- Active shown problem at start:
  - `src/pferdehof_bot/bot.py`: assignment to `intents.message_content` flagged by static checker.

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
- Status: **in progress**

### Phase 2: Shared transport extraction from core cog
- Scope:
  - extract response rendering and interaction context helpers.
  - keep command behavior unchanged.
- Status: pending

### Phase 3: View factory extraction
- Scope:
  - extract inline `discord.ui.View` classes from `core.py`.
  - centralize owner-guard/dispatch logic.
- Status: pending

### Phase 4: Readiness policy extraction
- Scope:
  - move train/ride readiness checks out of cog and into service-layer policy helpers.
- Status: pending

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
- 2026-03-28: Next step: run diagnostics + full pytest, then commit Phase 1.

## Next Actions
1. Validate no shown problems remain.
2. Run full pytest.
3. Commit Phase 1 and update this document with commit hash and results.
