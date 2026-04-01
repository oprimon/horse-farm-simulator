# Playdate Story Schema

This file defines an easy-to-extend content format for playdate stories so maintainers and players can submit funny story ideas in a consistent structure.

## Goals

- Keep playdates varied and memorable.
- Make stats influence flavor text (without filtering out stories).
- Support optional player cameos in the narrative.
- Keep reward math separate from writing so content can be expanded safely.

## Contribution Flow

1. Copy `docs/playdate_story_suggestions_template.json`.
2. Add or edit story entries.
3. Keep placeholders valid.
4. Open a PR with your new stories.

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

## Allowed Placeholders

Use only these placeholders in story lines:

- `{initiator_horse}`
- `{target_horse}`
- `{initiator_player}`
- `{target_player}`
- `{one_player}`

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
