# Refactor Handoff Plan (Dev Branch)

## Current Snapshot
- Branch: `dev`
- Current `HEAD`: `194f280` (`chore: stop tracking REFACTOR-HANDOFF-PLAN.md`)
- `origin/dev` in sync: yes
- Working tree status: clean (this file is intentionally untracked)
- Active shown problems: none
- Latest full test run: `166 passed`

## Objectives
1. Decompose `core.py` using SoC, DRY and DI — small, safe increments.
2. Run tests frequently (targeted while editing, full suite before every commit).
3. Keep all diagnostics clean throughout.
4. One commit per completed phase on `dev`; push immediately after each commit.
5. Delete this file once the refactor is complete.

---

## Implementation Phases

### Phase 1: Baseline + diagnostics cleanup ✅
- Removed `intents.message_content = False` in `src/pferdehof_bot/bot.py` — static typing fix; runtime behaviour unchanged (`Intents.default()` already disables message content).
- Commit: `a6a4233` · `fix(bot): resolve intents typing diagnostic and start refactor tracker`
- Verification: `166 passed`

### Phase 2: Shared transport extraction ✅
- **What**: extracted interaction-context resolution and response-rendering helpers out of `CoreCog` into a dedicated shared package.
- **Files added**:
  - `src/pferdehof_bot/cogs/shared/__init__.py`
  - `src/pferdehof_bot/cogs/shared/context.py` — `resolve_interaction_context`, `build_owner_display_name_map`
  - `src/pferdehof_bot/cogs/shared/responder.py` — `build_embed`, `send_response`, `respond_with_result`
- **`core.py` changes**: `CoreCog` delegates to these helpers; no behaviour change.
- Commit: `e757c3a` · `refactor(cogs): extract shared context and response transport helpers`
- Verification: targeted `37 passed`, full `166 passed`

### Phase 3: View factory extraction ⬜ NEXT
- **What**: move all inline `discord.ui.View` subclasses out of `core.py` into reusable view modules grouped by user journey. Replace repeated owner-guard callback boilerplate with one shared dispatch helper.
- **Target files to create**:
  - `src/pferdehof_bot/cogs/views/__init__.py`
  - `src/pferdehof_bot/cogs/views/onboarding_views.py` — candidate selection panel (`_build_candidate_view`)
  - `src/pferdehof_bot/cogs/views/action_views.py` — profile, recovery, progression, ride, post-ride, stable views
- **DRY target**: `ProfileActionView`, `RecoveryActionView`, `ProgressionActionView` share identical `_run` / owner-guard bodies → one shared base or dispatch function replaces them all.
- **Migration order** (run targeted tests after each):
  1. Extract `ChooseCandidateView` → `onboarding_views.py`; update `_build_candidate_view` in `core.py` to use it.
  2. Extract shared owner-guard dispatch → `action_views.py`.
  3. Extract remaining action views one family at a time.
  4. Remove all now-empty inline class definitions from `core.py`.
- **Test gate**: `tests/test_core_cog_slash.py` covers all view behaviour; must stay fully green after each migration step.
- Commit target: `refactor(cogs): extract interactive view factories into views package`

### Phase 4: Readiness policy extraction ✅
- **What**: moved `_can_train_from_player` / `_can_ride_from_player` domain thresholds from the cog into the progression service layer.
- **Files changed**:
  - `src/pferdehof_bot/services/progression.py` — added `can_train_player`, `can_ride_player`
  - `src/pferdehof_bot/cogs/core.py` — readiness methods now thin delegates to those helpers
- Commit: `e5285a9` · `refactor(progression): centralize ride and train readiness policy`
- Verification: targeted `47 passed`, full `166 passed`

### Phase 5: Multi-cog split ⬜ (depends on Phase 3)
- **What**: split `CoreCog` into four focused cogs by command domain. Each handler becomes: context extraction → service flow call → shared responder call (+ optional view factory).
- **Files to create**:
  - `src/pferdehof_bot/cogs/onboarding.py` — `/start`, `/greet`, `/horse` group (view / choose / name / profile / rename)
  - `src/pferdehof_bot/cogs/care.py` — `/feed`, `/groom`, `/rest`
  - `src/pferdehof_bot/cogs/progression.py` — `/train`, `/ride`
  - `src/pferdehof_bot/cogs/stable.py` — `/stable` (including async owner-name resolution)
- **`bot.py` change**: `DEFAULT_EXTENSIONS` updated from `core` to the four new cogs; `core.py` removed from loading.
- **Key constraint**: `horse_group = app_commands.Group(...)` must live in exactly one cog; avoid `CommandAlreadyRegistered` (see repo memory note).
- **Test gate**: `test_core_cog_registers_slash_commands` must still find all commands + subcommands + admin permission on `horse rename`.
- Commit target: `refactor(cogs): split CoreCog into domain-focused onboarding/care/progression/stable cogs`

### Phase 6: DI consolidation and hardening ⬜ (depends on Phase 5)
- **What**: construct repository and telemetry logger once at composition root; inject into every cog via `setup()` rather than each cog defaulting them internally.
- **Files to change**:
  - `src/pferdehof_bot/bot.py` — pass a shared dependency container to `load_extensions` / cog setup
  - All four split cogs — accept injected deps; remove default construction from `__init__`
- **Test gate**: DI wiring test (new), `test_bot_factory.py`, full `166+ passed`
- Commit target: `refactor(cogs): inject shared repository and telemetry dependencies at composition root`

---

## Test + Commit Cadence (mandatory)
- Targeted test run after every focused edit cluster.
- Full suite (`d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q`) before every commit.
- Never advance with a failing test.
- One commit per completed phase; push immediately.

## Quick Start (Next Session)
```
git checkout dev
git pull --ff-only origin dev
d:/Creativity/coding/Discord/pferdehof-sim/.venv/Scripts/python.exe -m pytest -q
# expect: 166 passed, clean working tree
# continue from Phase 3
```

## Completed Commit Timeline
| Commit | Message | Phase |
|---|---|---|
| `a6a4233` | fix(bot): resolve intents typing diagnostic and start refactor tracker | 1 |
| `e757c3a` | refactor(cogs): extract shared context and response transport helpers | 2 |
| `e5285a9` | refactor(progression): centralize ride and train readiness policy | 4 |
| `518d789` | docs(handoff): update tracker after readiness extraction push | tracker |
| `194f280` | chore: stop tracking REFACTOR-HANDOFF-PLAN.md | housekeeping |
