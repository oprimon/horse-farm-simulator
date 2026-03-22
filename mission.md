# Pferdehof Sim Mission

## Purpose

Build a Discord-native horse farm simulation that starts small, feels personal, and can grow into a richer social management game over time.

This is commission work and should remain a surprise, so we should avoid designing a giant system up front. The first version should prove that the core fantasy is fun:

- You get your own horse.
- You name it and care about it.
- You interact with it through short, playful Discord sessions.
- You feel progress over days, not just minutes.
- You can share some of that journey with other players.

## Discord Constraint

### Can the bot be added to only one channel?

Assumption based on Discord's bot model and docs:

- A bot is installed to a server, not natively to just one text channel.
- In practice, we can still make it behave like a channel-focused game by restricting permissions and command usage to one or a few channels.
- That means our product design should assume server install, but channel-scoped play is still feasible as an admin-controlled setup choice.

Practical consequence for MVP:

- We should support a designated "stable" or "farm" channel later.
- For the first MVP, it is enough if commands work server-wide while we keep the UX compatible with future channel restriction.

## Product Direction

Research-backed patterns from horse games such as Howrse, Star Stable, and Horse Reality:

- Strong emotional attachment to individual horses.
- Persistent care loops: feeding, grooming, resting, bonding.
- Growth and progression over time.
- Training into specialties, stats, and tricks.
- Light adventure or riding moments that create stories.
- Collection and legacy systems such as multiple horses, breeding, or bloodlines.
- Social play through collaboration, trading, shared events, or friendly competition.

For Discord, this suggests a low-friction format:

- Short command interactions.
- Daily or cooldown-based progression.
- Text-first storytelling.
- Shared social spaces with optional cooperative play.

## Five Lean Startup Assumptions

These assumptions are intentionally simple and testable. Each one can guide MVP scope.

### 1. Players want an emotional bond before they want complex systems

Hypothesis:
Players will engage more if their first meaningful action is receiving and naming a horse, rather than managing a large farm economy immediately.

Why this matters:

- Naming creates ownership fast.
- A single horse is easier to understand than a whole stable.
- Emotional attachment is likely the retention anchor for a Discord game.

Implication for MVP:

- Start with one horse per player.
- Make naming part of onboarding.
- Give the horse a visible identity: name, age or stage, mood, energy, trust.

How we validate:

- Track how many players who create a horse return the next day.
- Observe whether players reference their horse by name in chat.

### 2. Short interactive riding stories are more valuable than deep simulation at the start

Hypothesis:
Players will find a lightweight "ride" interaction with branching text outcomes more fun in early versions than a detailed simulation with many hidden stats.

Why this matters:

- Discord is strong at quick text interactions.
- Mini stories create surprise and personality.
- Early content can feel rich without building many systems.

Implication for MVP:

- Include a ride or outing command.
- Outcomes can depend on mood, energy, and trust.
- Results should be short, replayable, and occasionally memorable.

Examples:

- A calm forest ride.
- A muddy trail mishap.
- A chance to help another rider.
- A playful event where the horse reacts unexpectedly.

How we validate:

- Measure repeat use of the ride interaction.
- Note whether players share or quote favorite outcomes.

### 3. Care and training should be the first progression loop

Hypothesis:
Players will understand and stick with a loop of care -> train -> ride -> improve more easily than a complex farm management loop.

Why this matters:

- This loop is intuitive and genre-appropriate.
- It creates meaningful choices without overwhelming the player.
- It supports both nurturing and achievement motivations.

Implication for MVP:

- Core actions should be feed, groom, rest, train, ride.
- Training should unlock small progress in skills or tricks.
- Care should affect readiness and outcomes, not just be decorative.

Candidate early stats:

- Bond
- Energy
- Health
- Confidence
- Skill

Candidate early unlocks:

- Walk politely
- Trot steadily
- Small jump
- Trail confidence
- Friendly trick or pose

How we validate:

- Check whether players use both care and training, not just one command.
- Watch whether progression feels understandable without a tutorial wall.

### 4. Social play should be cooperative first, competitive second

Hypothesis:
For a commission surprise bot in Discord, collaboration will be a safer and more welcoming first social mechanic than rankings-heavy competition.

Why this matters:

- Discord communities often respond well to cooperative rituals.
- Cooperation reduces balance pressure in early development.
- It fits the horse-farm fantasy better than immediate leaderboards.

Implication for MVP:

- Add at least one cooperative interaction concept, even if very small.
- Avoid building a full competitive meta in version one.

Good early social ideas:

- Help another player care for a tired horse.
- Go on a group ride event.
- Contribute to a shared stable milestone.
- Send a small gift such as apples, brushes, or encouragement.

How we validate:

- Track whether players interact with each other through horse-related actions.
- Watch whether social actions improve return activity in small servers.

### 5. Time-based growth is enough for MVP; full breeding and farm economy can wait

Hypothesis:
Players will accept a simpler growth model at first if their horse visibly develops over time and unlocks new moments.

Why this matters:

- Breeding, genetics, and economy systems are expensive to design well.
- Many horse games use those systems successfully, but they are not required to prove the fantasy.
- A Discord bot should avoid complexity before the basic daily loop is working.

Implication for MVP:

- Use staged horse growth or progression milestones instead of full breeding.
- Delay systems like markets, bloodlines, and advanced ranch management.
- Focus on one horse becoming more capable and expressive over time.

Possible MVP progression model:

- New horse
- Settling in
- Confident companion
- Reliable riding horse

How we validate:

- See whether players stay engaged long enough to reach later stages.
- Gather feedback on whether one horse already feels meaningful.

## Proposed MVP

If we follow the assumptions above, the first MVP should likely include:

- Player starts with one horse.
- Player chooses a horse name.
- Horse has a small state model: mood, energy, bond, skill.
- Care actions: feed, groom, rest.
- Progress action: train.
- Fun action: ride with short interactive story outcomes.
- Riding outcomes are mostly positive in early versions and focus on bond or skill growth.
- A simple memory system so meaningful encounters can be revisited later.
- Slow growth over time through repeated play.
- One light social feature, preferably cooperative.

## Features Explicitly Out of MVP

To keep scope realistic, these should probably wait:

- Full breeding and genetics.
- Detailed farm building or land management.
- Complex item economy or marketplace.
- PvP-heavy competitions.
- Large numbers of horse breeds at launch.
- Deep admin configuration before core fun is proven.

## Candidate MVP Fantasy Statement

"Adopt a horse on your Discord server, care for it every day, train it, go on short text adventures, and grow a bond with it together with your friends."

## Decisions From Current Brainstorm

- Core emotional fantasy: "my first horse".
- Farm fantasy expansion: a shared stable emerges naturally as more players join and collaborate.
- Tone for early versions: playful and cozy.
- Magic direction: slightly magical elements are welcome later, not required for MVP.
- Social structure direction: one shared stable per server in later phases.
- Long-term extension idea: allow players to found their own stable in advanced versions.
- Riding outcomes in MVP: mostly wholesome and positive, focused on progression and good feelings.
- Simulation depth in MVP: prioritize accessibility and fun over strict realism.

## Social Memory Mechanic (New MVP Candidate)

Goal:
Create a lightweight system for shared stories between players without relying on direct messages.

Core idea:

- During ride outcomes, a player can generate a "memory" involving another player.
- The affected player sees this memory the next time they interact with the game.
- Players can review memories using a dedicated command, for example /memory or /mem.

Example flow:

1. Vera rides and gets an event where Ron needs help.
2. Vera chooses to help.
3. Ron receives a memory entry for later retrieval.
4. On next login, Ron gets a hint such as: "You have memories with Vera. Revisit them with /memory."

Why this fits Discord constraints:

- No dependence on unsolicited private messages.
- Social storytelling remains visible and retrievable through commands.
- Encourages player-to-player connection across different active times.

Why this is good for MVP:

- Adds emotional continuity with low system complexity.
- Reinforces cooperative identity without needing competitive systems.
- Can be implemented as simple text entries first, then expanded later.

## Recommended First Build Focus

If we want the safest first MVP direction, build around this loop:

1. Adopt horse
2. Name horse
3. Care for horse
4. Train horse
5. Ride horse in a mini story and create memories
6. Share progress with friends

That is enough to test whether the bot has heart before we invest in deeper systems.