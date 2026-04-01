# Playdate Story Schema

This file defines an easy-to-extend content format for playdate stories so maintainers and players can submit funny story ideas in a consistent structure.

## Goals

- Keep playdates varied and memorable.
- Make stats influence flavor text (without filtering out stories).
- Support optional player cameos in the narrative.
- Keep reward math separate from writing so content can be expanded safely.

## Contribution Flow

1. Create a new JSON file in the `stories/` folder (e.g. `stories/my_ideas.json`).
2. Use `docs/playdate_story_suggestions_template.json` as a starting point for the entry shape.
3. Add one or more story objects inside the `"stories"` array.
4. Keep all placeholders valid (see Allowed Placeholders below).
5. Open a PR — the engine scans every `*.json` file in `stories/` automatically on each `/playdate` call, so your stories go live as soon as the PR merges without any code change or restart.

## Template Fields

Each story entry uses this shape:

```json
{
  "story_id": "apple_diplomacy",
  "tone": "cozy",
  "title": "Apple Diplomacy",
  "weight": 9,
  "opening_lines": [
    "A single apple appears, and {initiator_horse} and {target_horse} begin careful negotiations."
  ],
  "event_lines": [
    "Every sniff is followed by a pause as if both horses are drafting amendments."
  ],
  "ending_lines": [
    "They finish with shared crunches and a visible increase in mutual respect."
  ],
  "cameo_none_lines": [
    "The stable agrees this was diplomacy at its finest."
  ],
  "cameo_one_lines": [
    "{one_player} arrives with a backup snack and instantly becomes foreign aid."
  ],
  "cameo_both_lines": [
    "{initiator_player} and {target_player} call it training; the horses call it lunch policy."
  ]
}
```

## Message Structure

The engine assembles each playdate message in this fixed order:

```
[opening] [energy stat] [confidence stat] [bond stat] [event] [cameo] [ending]
```

The stat and cameo fragments are injected automatically — story files only need to provide the five line groups: `opening_lines`, `event_lines`, `ending_lines`, and the three `cameo_*_lines`.

**Tips per field:**

- **opening_lines** — Set the scene. The very next sentence the engine adds will describe how one of the horses is feeling energy-wise, so avoid energy or tiredness references here.
- **event_lines** — Describe the main action. This line follows directly after a stat sentence such as *"Nova settles into a steady rhythm…"*. Write events that read naturally after that kind of flavor.
- **ending_lines** — Punch-line close. Written after the cameo line. Keep it standalone and satisfying; it should feel complete whether a player name appeared just before or not.
- **cameo_none_lines** — Stable or environment observation when no player cameo fires. Do not reference player placeholders here.
- **cameo_one_lines** — One randomly selected player appears. Use only `{one_player}` here; do **not** use `{initiator_player}` or `{target_player}` (they will render as literal text).
- **cameo_both_lines** — Both players appear. Use `{initiator_player}` and `{target_player}`. Do not use `{one_player}` here.

## Allowed Placeholders

Use only these placeholders in story lines:

- `{initiator_horse}` — available in all six line groups
- `{target_horse}` — available in all six line groups
- `{initiator_player}` — available in all six line groups, but only meaningful in `cameo_both_lines`
- `{target_player}` — available in all six line groups, but only meaningful in `cameo_both_lines`
- `{one_player}` — **only** valid in `cameo_one_lines` and `cameo_both_lines`; causes a runtime error if used in `opening_lines`, `event_lines`, or `ending_lines`

## Writing Guidelines

- Keep each line short (1 sentence).
- Prefer playful/cozy tone over mean-spirited outcomes.
- Avoid explicit harassment content.
- Keep stories readable when any cameo mode is selected.
- Endings should feel punchy and memorable.

## Stat-Reactive Style

Stats should alter inserted flavor fragments (energy/confidence/bond), not gate whether a story can roll.

Example:

- Low energy variant: "Although a little tired, {target_horse} still keeps pace with stubborn determination."
- High confidence variant: "{initiator_horse} takes point like a self-appointed tour guide."

This keeps story variety high while still making horse state feel meaningful.
