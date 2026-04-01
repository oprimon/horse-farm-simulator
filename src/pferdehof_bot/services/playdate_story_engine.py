"""Playdate story generation with stat-reactive narrative variants."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
import string


_CAMEO_NONE = "none"
_CAMEO_ONE = "one"
_CAMEO_BOTH = "both"

# Allowed placeholders per line field — violations are caught at load time.
# opening/event/ending lines are formatted with horse names and player names but NOT {one_player}.
# cameo lines are formatted with player names and {one_player} but NOT horse names.
_STORY_LINE_ALLOWED = frozenset({"initiator_horse", "target_horse", "initiator_player", "target_player"})
_CAMEO_LINE_ALLOWED = frozenset({"initiator_player", "target_player", "one_player"})
_PLACEHOLDER_RULES: dict[str, frozenset[str]] = {
    "opening_lines": _STORY_LINE_ALLOWED,
    "event_lines": _STORY_LINE_ALLOWED,
    "ending_lines": _STORY_LINE_ALLOWED,
    "cameo_none_lines": _CAMEO_LINE_ALLOWED,
    "cameo_one_lines": _CAMEO_LINE_ALLOWED,
    "cameo_both_lines": _CAMEO_LINE_ALLOWED,
}


@dataclass(frozen=True)
class PlaydateStoryTemplate:
    """Single playdate story template entry."""

    story_id: str
    tone: str
    title: str
    weight: int
    opening_lines: tuple[str, ...]
    event_lines: tuple[str, ...]
    ending_lines: tuple[str, ...]
    cameo_none_lines: tuple[str, ...]
    cameo_one_lines: tuple[str, ...]
    cameo_both_lines: tuple[str, ...]


@dataclass(frozen=True)
class PlaydateStoryContext:
    """Runtime context used to render playdate story variants."""

    initiator_horse_name: str
    target_horse_name: str
    initiator_player_name: str
    target_player_name: str
    initiator_energy: int
    target_energy: int
    initiator_confidence: int
    target_confidence: int
    initiator_bond: int
    target_bond: int
    initiator_health: int
    target_health: int


@dataclass(frozen=True)
class PlaydateNarrative:
    """Rendered narrative output for one playdate."""

    story_id: str
    tone: str
    title: str
    message: str


DEFAULT_PLAYDATE_STORIES: tuple[PlaydateStoryTemplate, ...] = (
    PlaydateStoryTemplate(
        story_id="brush_conspiracy",
        tone="funny",
        title="The Brush Conspiracy",
        weight=10,
        opening_lines=(
            "{initiator_horse} and {target_horse} discover a grooming brush placed way too neatly in the aisle.",
            "A suspiciously shiny grooming brush appears, and {initiator_horse} immediately treats it like a relic.",
        ),
        event_lines=(
            "They investigate in dramatic circles and somehow conclude the brush must be guarded.",
            "Both horses perform an extremely serious inspection routine that convinces nobody and everyone.",
        ),
        ending_lines=(
            "By the end, the brush is exactly where it started and somehow far more important.",
            "The mystery remains unsolved, but morale in the stable rises significantly.",
        ),
        cameo_none_lines=(
            "No human witnesses step in, so the official report is left to hoofprint interpretation.",
        ),
        cameo_one_lines=(
            "{one_player} tries to restore order and accidentally validates the conspiracy.",
        ),
        cameo_both_lines=(
            "{initiator_player} and {target_player} exchange one look that means: let them cook.",
        ),
    ),
    PlaydateStoryTemplate(
        story_id="apple_diplomacy",
        tone="cozy",
        title="Apple Diplomacy",
        weight=9,
        opening_lines=(
            "A single apple appears, and {initiator_horse} and {target_horse} begin careful negotiations.",
            "{target_horse} spots an apple and invites {initiator_horse} into a very official treaty process.",
        ),
        event_lines=(
            "Every sniff is followed by a pause as if both horses are drafting amendments.",
            "The discussion remains peaceful, with occasional nose-boops serving as signatures.",
        ),
        ending_lines=(
            "They finish with shared crunches and a visible increase in mutual respect.",
            "The final treaty outcome: one apple, two very satisfied horses.",
        ),
        cameo_none_lines=(
            "The stable agrees this was diplomacy at its finest.",
        ),
        cameo_one_lines=(
            "{one_player} arrives with a backup snack and instantly becomes foreign aid.",
        ),
        cameo_both_lines=(
            "{initiator_player} and {target_player} call it training; the horses call it lunch policy.",
        ),
    ),
    PlaydateStoryTemplate(
        story_id="puddle_sprint",
        tone="chaos-lite",
        title="Puddle Sprint",
        weight=8,
        opening_lines=(
            "A tiny puddle becomes a full obstacle course the moment {initiator_horse} notices it.",
            "{target_horse} declares the puddle lane open, and {initiator_horse} accepts immediately.",
        ),
        event_lines=(
            "Two cautious steps escalate into a surprisingly elegant splash routine.",
            "They alternate hops like a synchronized team that forgot to register.",
        ),
        ending_lines=(
            "The puddle wins no trophies, but the audience gives thunderous approval anyway.",
            "Final score: puddle 0, joy 100.",
        ),
        cameo_none_lines=(
            "The stable floor dries eventually; the story does not.",
        ),
        cameo_one_lines=(
            "{one_player} attempts to keep things dry and is politely ignored.",
        ),
        cameo_both_lines=(
            "{initiator_player} and {target_player} briefly discuss cleanup logistics, then applaud.",
        ),
    ),
    PlaydateStoryTemplate(
        story_id="ribbon_heist",
        tone="funny",
        title="The Ribbon Heist",
        weight=8,
        opening_lines=(
            "A decorative ribbon goes missing right as {target_horse} starts looking suspiciously proud.",
            "{initiator_horse} finds a ribbon and instantly assumes command of an undercover mission.",
        ),
        event_lines=(
            "One horse carries the prize while the other provides dramatic lookout services.",
            "They parade through the aisle as if this was always the official plan.",
        ),
        ending_lines=(
            "The ribbon is returned with honor and exactly zero explanation.",
            "No rules are broken on record, yet everyone feels mildly outplayed.",
        ),
        cameo_none_lines=(
            "A nearby pony sighs in admiration at the operational discipline.",
        ),
        cameo_one_lines=(
            "{one_player} asks who started this; both horses refuse to comment.",
        ),
        cameo_both_lines=(
            "{initiator_player} and {target_player} hold a quick trial and immediately acquit both suspects.",
        ),
    ),
    PlaydateStoryTemplate(
        story_id="gate_patrol",
        tone="cozy",
        title="Gate Patrol",
        weight=7,
        opening_lines=(
            "{initiator_horse} and {target_horse} volunteer for an unscheduled gate safety inspection.",
            "A quiet corner near the gate turns into patrol duty for two very committed horses.",
        ),
        event_lines=(
            "They perform deliberate laps and pause to approve each hinge with solemn nods.",
            "The inspection includes extra sniffs, careful pacing, and occasional proud snorting.",
        ),
        ending_lines=(
            "Security remains excellent, and both horses leave with heroic energy.",
            "The patrol wraps up with a shared stance that says job well done.",
        ),
        cameo_none_lines=(
            "The stable ledger records this as preventive maintenance with style.",
        ),
        cameo_one_lines=(
            "{one_player} thanks the patrol officers and receives a very professional nod.",
        ),
        cameo_both_lines=(
            "{initiator_player} and {target_player} pretend this was planned all along.",
        ),
    ),
    PlaydateStoryTemplate(
        story_id="hat_rehearsal",
        tone="funny",
        title="Hat Rehearsal",
        weight=6,
        opening_lines=(
            "Someone leaves a hat on the fence and {target_horse} appoints it as rehearsal equipment.",
            "{initiator_horse} spots a hat and decides this requires immediate choreography.",
        ),
        event_lines=(
            "The routine includes gentle bows, dramatic turns, and one perfectly timed snort.",
            "They circle the hat like a stage prop while practicing very serious posture.",
        ),
        ending_lines=(
            "The hat survives. Confidence levels do not return to normal.",
            "By the finale, both horses look ready for opening night.",
        ),
        cameo_none_lines=(
            "Critics agree the performance was experimental and excellent.",
        ),
        cameo_one_lines=(
            "{one_player} attempts direction and is quickly outdirected.",
        ),
        cameo_both_lines=(
            "{initiator_player} and {target_player} become audience members in row one.",
        ),
    ),
)


def load_story_packs_from_folder(folder: Path) -> tuple[PlaydateStoryTemplate, ...]:
    """Load all story pack JSON files from a folder. Invalid files are skipped silently."""
    if not folder.is_dir():
        return ()
    stories: list[PlaydateStoryTemplate] = []
    for json_file in sorted(folder.glob("*.json")):
        try:
            with json_file.open(encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("stories", []):
                try:
                    stories.append(_json_to_story_template(entry))
                except (KeyError, TypeError, ValueError):
                    pass  # Skip individual malformed entries
        except Exception:
            pass  # Skip unreadable or malformed files
    return tuple(stories)


def _json_to_story_template(data: dict) -> PlaydateStoryTemplate:
    template = PlaydateStoryTemplate(
        story_id=str(data["story_id"]),
        tone=str(data["tone"]),
        title=str(data["title"]),
        weight=max(1, int(data.get("weight", 7))),
        opening_lines=tuple(str(line) for line in data.get("opening_lines", [])),
        event_lines=tuple(str(line) for line in data.get("event_lines", [])),
        ending_lines=tuple(str(line) for line in data.get("ending_lines", [])),
        cameo_none_lines=tuple(str(line) for line in data.get("cameo_none_lines", [])),
        cameo_one_lines=tuple(str(line) for line in data.get("cameo_one_lines", [])),
        cameo_both_lines=tuple(str(line) for line in data.get("cameo_both_lines", [])),
    )
    for field_name, allowed in _PLACEHOLDER_RULES.items():
        _validate_line_placeholders(getattr(template, field_name), allowed, field_name)
    return template


def _validate_line_placeholders(lines: tuple[str, ...], allowed: frozenset[str], field: str) -> None:
    """Raise ValueError if any line uses a placeholder not in allowed."""
    for line in lines:
        for _, field_key, _, _ in string.Formatter().parse(line):
            if field_key is not None and field_key not in allowed:
                raise ValueError(
                    f"Illegal placeholder {{{field_key}}} in {field}. "
                    f"Allowed: {sorted(allowed)}"
                )


def render_playdate_narrative(
    context: PlaydateStoryContext,
    *,
    rng: random.Random | None = None,
    story_id_override: str | None = None,
    cameo_override: str | None = None,
    story_packs_dir: Path | None = None,
) -> PlaydateNarrative:
    """Render one playdate narrative from a template plus stat-reactive fragments."""
    resolved_rng = rng or random.Random()
    all_stories = DEFAULT_PLAYDATE_STORIES
    if story_packs_dir is not None:
        loaded = load_story_packs_from_folder(story_packs_dir)
        if loaded:
            all_stories = loaded
    story = _choose_story(all_stories, resolved_rng, story_id_override)
    cameo_mode = cameo_override or _choose_cameo_mode(resolved_rng)

    line_pool = _format_line_pool(story.opening_lines, context)
    event_pool = _format_line_pool(story.event_lines, context)
    ending_pool = _format_line_pool(story.ending_lines, context)

    opening = resolved_rng.choice(line_pool)
    event = resolved_rng.choice(event_pool)
    ending = resolved_rng.choice(ending_pool)

    stat_line = _build_stat_line(context, resolved_rng)
    cameo_line = _build_cameo_line(story=story, context=context, cameo_mode=cameo_mode, rng=resolved_rng)

    message = " ".join((opening, stat_line, event, cameo_line, ending)).strip()
    return PlaydateNarrative(
        story_id=story.story_id,
        tone=story.tone,
        title=story.title,
        message=message,
    )


def _choose_story(
    stories: tuple[PlaydateStoryTemplate, ...],
    rng: random.Random,
    story_id_override: str | None,
) -> PlaydateStoryTemplate:
    if story_id_override:
        for story in stories:
            if story.story_id == story_id_override:
                return story

    weights = [max(1, int(story.weight)) for story in stories]
    return rng.choices(population=list(stories), weights=weights, k=1)[0]


def _choose_cameo_mode(rng: random.Random) -> str:
    roll = rng.randint(1, 100)
    if roll <= 55:
        return _CAMEO_NONE
    if roll <= 85:
        return _CAMEO_ONE
    return _CAMEO_BOTH


def _format_line_pool(lines: tuple[str, ...], context: PlaydateStoryContext) -> tuple[str, ...]:
    return tuple(
        line.format(
            initiator_horse=context.initiator_horse_name,
            target_horse=context.target_horse_name,
            initiator_player=context.initiator_player_name,
            target_player=context.target_player_name,
        )
        for line in lines
    )


def _build_stat_line(context: PlaydateStoryContext, rng: random.Random) -> str:
    """Build one blended stat-reactive sentence for energy and confidence flavor."""
    lower_energy_horse = context.initiator_horse_name
    lower_energy_value = context.initiator_energy
    if context.target_energy < context.initiator_energy:
        lower_energy_horse = context.target_horse_name
        lower_energy_value = context.target_energy

    lower_conf_horse = context.initiator_horse_name
    lower_conf_value = context.initiator_confidence
    if context.target_confidence < context.initiator_confidence:
        lower_conf_horse = context.target_horse_name
        lower_conf_value = context.target_confidence

    energy_line = _energy_variant(horse_name=lower_energy_horse, value=lower_energy_value, rng=rng)
    confidence_line = _confidence_variant(horse_name=lower_conf_horse, value=lower_conf_value, rng=rng)
    bond_line = _bond_variant(
        initiator_horse=context.initiator_horse_name,
        target_horse=context.target_horse_name,
        average_bond=(context.initiator_bond + context.target_bond) // 2,
        rng=rng,
    )
    return f"{energy_line} {confidence_line} {bond_line}".strip()


def _energy_variant(*, horse_name: str, value: int, rng: random.Random) -> str:
    if value < 35:
        return rng.choice(
            (
                f"Although a little tired, {horse_name} still keeps up with stubborn determination.",
                f"Even while winded, {horse_name} refuses to miss a single turn of the fun.",
            )
        )
    if value < 70:
        return rng.choice(
            (
                f"{horse_name} settles into a steady rhythm and stays right in the middle of the action.",
                f"{horse_name} paces smoothly and keeps the playdate comfortably lively.",
            )
        )
    return rng.choice(
        (
            f"{horse_name} bursts forward with extra energy, then loops back like an excited guide.",
            f"With energy to spare, {horse_name} turns each small moment into a full event.",
        )
    )


def _confidence_variant(*, horse_name: str, value: int, rng: random.Random) -> str:
    if value < 35:
        return rng.choice(
            (
                f"{horse_name} pauses once, then bravely chooses curiosity over caution.",
                f"After one careful glance around, {horse_name} joins in with growing courage.",
            )
        )
    if value < 70:
        return rng.choice(
            (
                f"{horse_name} checks in, then commits to the game with calm confidence.",
                f"{horse_name} reads the moment well and follows through with steady focus.",
            )
        )
    return rng.choice(
        (
            f"{horse_name} takes point like a self-appointed tour guide and commits to the bit.",
            f"Feeling bold, {horse_name} treats every cue like a chance to perform.",
        )
    )


def _bond_variant(*, initiator_horse: str, target_horse: str, average_bond: int, rng: random.Random) -> str:
    if average_bond < 35:
        return rng.choice(
            (
                f"{initiator_horse} and {target_horse} keep a polite distance, but their timing starts to sync.",
                f"They stay respectfully cautious, yet mirror each other more with every minute.",
            )
        )
    if average_bond < 70:
        return rng.choice(
            (
                f"They naturally fall into step and trade curious glances throughout the scene.",
                f"The pair settles into an easy rhythm that looks increasingly deliberate.",
            )
        )
    return rng.choice(
        (
            f"They move like a practiced duo, anticipating each other before each tiny turn.",
            f"Their teamwork lands so cleanly it almost looks rehearsed.",
        )
    )


def _build_cameo_line(
    *,
    story: PlaydateStoryTemplate,
    context: PlaydateStoryContext,
    cameo_mode: str,
    rng: random.Random,
) -> str:
    one_player = context.initiator_player_name if rng.randint(0, 1) == 0 else context.target_player_name
    format_kwargs = {
        "initiator_player": context.initiator_player_name,
        "target_player": context.target_player_name,
        "one_player": one_player,
    }

    if cameo_mode == _CAMEO_BOTH:
        pool = story.cameo_both_lines
    elif cameo_mode == _CAMEO_ONE:
        pool = story.cameo_one_lines
    else:
        pool = story.cameo_none_lines

    return rng.choice(pool).format(**format_kwargs)