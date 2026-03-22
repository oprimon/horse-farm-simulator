# MVP-001: Horse Creation ("My First Horse")

## Goal
Validate the core emotional fantasy quickly:
- "I got my own horse."
- "I chose it."
- "I named it."
- "I want to come back tomorrow."

## Recommendation (Implementation + Product)
For MVP-001, do **not** build a full horse creator.

Use a **pick-one flow from a small random set**:
1. Player runs `/start`.
2. Bot shows 3 generated horses (short profile each).
3. Player inspects and chooses one.
4. Player gives it a name.
5. Horse is permanently assigned to that player.

Why this is best for MVP:
- Lower implementation cost than full custom creation UI.
- More emotional ownership than a single fully-random assignment.
- Creates a small "meeting your horse" moment before naming.
- Easy to expand later (more archetypes, rarity, traits, breeds, etc.).

## Assumption To Test In The Wild
Primary assumption:
Players feel stronger attachment and better early retention when they can choose from a few horse candidates and then name one, compared to receiving a single random horse with no choice.

Success signals (first 1-2 weeks):
- >= 70% of players who start onboarding complete horse adoption.
- >= 60% of adopters return within 48 hours.
- >= 40% of adopters run at least one horse interaction command after adoption (`/feed`, `/groom`, `/ride`, etc.).
- Qualitative signal: players refer to horse by name in chat.

Failure signals:
- Many players drop during selection step.
- Players skip naming or use default/random names disproportionately.
- Low next-day return despite completed adoption.

## Minimal Feature Set (Discord MVP)
### 1. Onboarding and ownership
- One horse per player.
- `/start` creates onboarding session.
- Player cannot adopt a second horse.

### 2. Candidate generation
- Generate exactly 3 horses per onboarding session.
- Each candidate contains only:
  - Temporary id (A/B/C)
  - Appearance text (very lightweight, e.g. coat color + marking)
  - 1 hinted strength (e.g. "sure-footed", "calm", "quick learner")
- Keep stats hidden as numbers in MVP; only show hints.

### 3. Selection
- `/horse view` (or button/select menu) to review candidates.
- `/horse choose <id>` locks chosen candidate.
- Choice is irreversible in MVP (simple rule, simple data model).

### 4. Naming
- `/horse name <name>` required to finish adoption.
- Name validation:
  - length 2-20
  - basic profanity filter (or blocklist)
- Once set, name can only be changed by admin command later (or not at all in MVP).

### 5. First identity display
- `/horse` shows: name, appearance, 1-2 visible traits, mood/energy baseline.
- First confirmation message should feel celebratory and personal.

### 6. Minimal persistence
Store per player (and per guild if needed):
- adopted flag
- horse seed/template id
- finalized appearance/traits
- chosen hint/archetype
- horse name
- created_at

### 7. Post-adoption tiny loop hook
At least one immediate interaction command after adoption:
- `/greet` or `/feed` (single lightweight response)
So adoption is not a dead end.

## Random Stats vs Full Creator vs Pick-One
### Option A: Fully random horse assigned
Pros:
- Fastest implementation.

Cons:
- Lower player agency.
- Weaker ownership feeling.
- Harder to create "I chose this horse" attachment.

### Option B: Full horse creator
Pros:
- Maximum agency.

Cons:
- Highest scope and UI complexity.
- Slower to ship and balance.
- Risks overbuilding before fun is validated.

### Option C: Choose from 3 generated horses (recommended)
Pros:
- Strong agency with low complexity.
- Supports emotional story of "meeting" horses.
- Easy to implement with slash commands and embeds.

Cons:
- Slightly more logic than pure random assignment.

## What Must Also Be Documented Next
Create follow-up docs for:

1. Command contract
- Exact slash commands, arguments, and response messages.
- Error states and recovery messages.

2. Data model and storage
- Player record schema.
- Horse schema fields.
- Guild scoping rules.
- Migration strategy for future traits/stats.

3. Candidate generation rules
- Trait pools.
- Weighting/rarity (if any).
- Deterministic seed strategy (important for reproducibility/debugging).

4. UX copy and tone
- Onboarding text variants.
- Confirmation and failure copy.
- Cozy/playful voice guidelines.

5. Telemetry and experiment plan
- Events to log (start_onboarding, viewed_candidates, chose_candidate, named_horse, first_interaction).
- Funnel dashboard definition.
- Success thresholds and decision date.

6. Moderation and safety
- Naming policy.
- Profanity handling.
- Admin override tools.

7. Out-of-scope guardrails
- No breeding/genetics.
- No economy/market.
- No advanced horse editor.

## MVP-001 Exit Criteria
MVP-001 is successful when:
- Players can reliably adopt exactly one horse through choose + name flow.
- Data persists across restarts.
- Funnel metrics are captured.
- At least one interaction after adoption is used by a meaningful share of players.

Then proceed to MVP-002 (care + training + first ride outcomes).