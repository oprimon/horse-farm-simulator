# MVP-002: Care, Training, and First Ride

## Goal
Validate the first repeatable daily loop after adoption:
- "I can care for my horse."
- "My horse changes based on what I do."
- "Short rides create small stories I want to revisit."
- "I want to come back tomorrow because progress feels personal."

## Recommendation (Implementation + Product)
For MVP-002, do not build a full farm sim, economy, or multi-horse stable.

Use a lightweight care -> train -> ride loop for players who already completed MVP-001:
1. Player checks on their horse.
2. Player uses one or more care actions.
3. Player trains their horse.
4. Player goes on a short ride.
5. Players can open a stable roster view to see all adopted horses in the server.
6. Bot returns a personalized outcome with visible state changes.
7. Player has a reason to return later as energy, confidence, and bond continue evolving.

Why this is best for MVP-002:
- Directly follows the mission assumption that care and training should be the first progression loop.
- Preserves Discord-friendly short sessions instead of long management screens.
- Builds attachment through repeated interaction with one horse rather than expanding breadth too early.
- Creates room for later systems such as memories, social play, tricks, and events without forcing them now.

Delivery rule:
- MVP-002 player-facing interactions are implemented as Discord Slash Commands.
- This includes both newly introduced loop commands and existing player-facing commands from current runtime behavior.
- A command registry layer should define slash command names, ownership, and visibility in one place.

## Assumption To Test In The Wild
Primary assumption:
Players who have already adopted a horse will return more often if they can run a simple care and training loop that meaningfully affects ride outcomes.

Success signals (first 1-2 weeks after MVP-002 release):
- >= 60% of adopters use at least one care command within 48 hours.
- >= 45% of adopters use both `/train` and `/ride` within their first 3 days.
- >= 35% of adopters complete at least two loop sessions on different days.
- Qualitative signal: players talk about how their horse behaved on a ride, not just that they own one.

Failure signals:
- Players only run one command repeatedly and ignore the rest of the loop.
- Ride outcomes feel disconnected from care and training state.
- State feels too hidden or too complex, causing confusion instead of attachment.
- Players stop after one ride because there is no felt progression.

## Minimal Feature Set (Discord MVP)
### 0. Slash command migration and command registry foundation
- Migrate current player-facing prefix commands to slash command equivalents:
  - `/start`
  - `/horse` with subcommand coverage for view, choose, and name
  - `/greet`
- Define a command registry so command metadata is centralized and consistent.
- Registry should include at least:
  - command and subcommand names
  - visibility intent (ephemeral or channel-visible)
  - permission constraints (for example admin-only rename behavior)
- Add startup sync behavior for slash command registration in development and production-safe usage.

### 1. Horse state model
- Extend the adopted horse with a small progression state:
  - Bond
  - Energy
  - Health
  - Confidence
  - Skill
- Keep raw numbers hidden or lightly abstracted in player-facing text.
- Show readable status bands such as low, steady, eager, tired, or confident.

### 1.1 Dice and attribute-check rules (MVP-002 baseline)
- State values are clamped to `0..100`.
- `increases`: always add the rolled amount and clamp to max `100`.
- `decreases`: always subtract the rolled amount and clamp to min `0`.
- `has a chance to increase`: roll `1d100`; if roll is higher than the current checked value, apply the configured increase roll amount (for this MVP baseline, `1d10`, max `100`).
- `has a chance (<attribute>) to decrease`: roll `1d100` against `<attribute>`; if roll is higher than `<attribute>`, decrease the target stat by the configured decrease roll amount (min `0`).
- `has a slight chance (<attribute>) to decrease`: roll `1d100` twice against `<attribute>`; only if both rolls are higher than `<attribute>`, decrease the target stat by the configured decrease roll amount.
- Design note for consistency: `d100` is used for checks, while `d10` rolls are used as actual stat deltas.

### 2. Care actions
- Add care commands:
  - `/feed`
  - `/groom`
  - `/rest`
- Baseline effects:
  - `/feed`: energy always increases by `1d10` (max `100`).
  - `/groom`: choose bond or health, then perform a chance-to-increase check; on success increase chosen stat by `1d10` (max `100`).
  - `/rest`: health always increases by `1d10` (max `100`).
- Commands should be short, flavorful, and personalized to the horse's name.

### 3. Training action
- Add `/train` as the core progress action.
- Baseline effects:
  - Chance to increase skill by `1d10` (max `100`) using a `1d100` vs current skill check.
  - Slight chance (skill check) to decrease health by `1d10` (min `0`) using two `1d100` rolls.
- Optional readiness gating (for example low health refusal) may still be used, but this baseline defines train risk/reward without a required guaranteed energy cost.

### 4. First ride loop
- Add `/ride` with short text outcomes.
- Outcomes should depend on current horse state and recent actions.
- Baseline state effects:
  - Chance to increase confidence or bond by `1d10` (max `100`) using a `1d100` check against the selected target stat.
  - Energy always decreases by `3d10` (min `0`).
  - Chance (skill check) to decrease health by `1d10` (min `0`) using `1d100` vs skill.
- Early ride results should skew wholesome and encouraging.
- Occasional soft setbacks are allowed, but should feel recoverable rather than punishing.

### 5. Horse profile evolution
- Expand `/horse` so it reflects the new loop:
  - current mood or readiness text
  - visible progress summary
  - last meaningful activity or recent ride note
- Preserve the cozy, personal tone from MVP-001.

### 6. Stable roster command
- Add `/stable` to show all adopted horses in the current guild.
- Each row should include:
  - horse id
  - horse name
  - owner display name
- Sort output in a predictable order and keep formatting readable for busy channels.
- If no horses are adopted yet, return encouraging guidance.

### 7. Time-based pacing
- Add light pacing so progress happens over days, not only minutes.
- Prefer simple timestamps, soft cooldowns, or recovery windows over hard simulation.
- Avoid building a complex scheduler or offline simulation engine.

### 8. Minimal persistence
Store per adopted horse:
- state values or bands for bond, energy, health, confidence, skill
- last action timestamps per command category if needed
- latest ride summary or recent activity snippet
- progression timestamps needed for recovery or telemetry

Store per guild roster display needs:
- stable-scoped horse id that is unique within the guild
- owner display reference or owner id resolvable to display name at render time

### 9. Telemetry and balancing
Track which actions players use and whether the loop converts into repeat sessions.

Required MVP-002 events:
- `fed_horse`
- `groomed_horse`
- `rested_horse`
- `trained_horse`
- `rode_horse`
- `ride_outcome`
- `viewed_stable`

## Why This Scope, Not More
This MVP should prove the solo attachment loop before expanding sideways.

Specifically out of scope for MVP-002:
- Full inventory or item economy
- Breeding, genetics, or multiple horses per player
- Competitive rankings
- Complex injury systems
- Large breed catalogs
- Rich cooperative systems beyond telemetry-ready hooks
- Full memory inbox or cross-player story delivery

## What Must Also Be Documented Next
Create follow-up docs for:

1. Command contract
- Exact slash commands, cooldown expectations, and state-related failure copy.
- Include `/stable` payload rules, sorting rules, and empty-state copy.
- Include migration mapping from old prefix commands to slash commands.

2. Command registry and sync rules
- Registry ownership and update process.
- Which command fields are source-of-truth and how handlers bind to them.
- Slash sync strategy and safety notes for rollout.

3. Horse state and balancing rules
- Starting values or bands.
- Caps, floors, and recovery rules.
- Which actions affect which state dimensions.

4. Ride outcome design
- Outcome pools.
- State-based weighting.
- Safe failure tone and recovery rules.

5. UX copy and tone
- Cozy, personal, short, and readable in a busy Discord channel.

6. Telemetry and experiment plan
- Action frequency.
- Loop completion rates.
- Multi-day return behavior after first ride.

7. Out-of-scope guardrails
- No economy creep.
- No deep admin tooling.
- No social mechanics that require large coordination overhead.

## MVP-002 Exit Criteria
MVP-002 is successful when:
- Adopted players can use care commands, train, and ride reliably.
- Horse state changes persist across restarts.
- Ride outcomes visibly reflect horse state.
- The bot records enough telemetry to measure loop completion and repeat usage.
- The resulting loop is engaging enough to justify MVP-003 social or memory systems.

Then proceed to MVP-003 (shared stable memories, cooperative play, and broader progression).