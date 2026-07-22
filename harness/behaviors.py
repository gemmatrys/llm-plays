"""Behavior library: builtins + YAML-defined skills.

A skill file (skills/<scope>/<name>.yaml) looks like:

    name: heal_at_center
    description: From outside a Pokémon Center door, enter, heal, exit.
    steps:
      - {button: UP, hold_frames: 8, wait_frames: 30}     # press-and-release
      - {button: A, hold_frames: 8, wait_frames: 60}
      ...

Key up/down sequences (combos, holds) use explicit ops; keys still down when the
behavior ends are auto-released by the executor, so a forgotten keyup or an
aborted plan can never leave a button stuck:

    steps:
      - {op: keydown, button: B, wait_frames: 2}          # hold B (run)...
      - {button: UP, hold_frames: 30, wait_frames: 0}     # ...while walking up
      - {button: UP, hold_frames: 30, wait_frames: 0}
      - {op: keyup, button: B}

Claude checkpoints grow this library over time; the local LLM selects from it by name.
"""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml

from .types import Behavior, Step


def _builtin(name: str, steps: list[Step],
             desc: str | None = None) -> Behavior:
    return Behavior(name=name, steps=steps, source="builtin",
                    description=desc)


# family lines for the served allowed-behaviors listing: counted walks and
# single presses would be ~45 near-identical entries; one line each family
FAMILY_LINES = [
    ("walk_north / walk_south / walk_west / walk_east",
     "stride STRAIGHT that way until something stops you (~12 tiles), "
     "sidestepping a lone obstacle and hopping ledges downward; reports how "
     "far it went and every side opening it passed - openings are how mazes "
     "continue. At an area's edge one more step crosses into the next area. "
     "Repeating it after a stop just bumps the same wall."),
    ("walk_<direction>_<1-9>",
     "walk EXACTLY that many tiles (a '3 south, 4 east' bearing = "
     "walk_south_3, walk_east_4). Straight walks stop BESIDE doors - a "
     "single press steps through."),
    ("press_UP / press_DOWN / press_LEFT / press_RIGHT / press_A / "
     "press_B / press_START / press_SELECT",
     "one single press: fine positioning (one step), A talks to what you "
     "face or answers YES, B answers NO or backs out, START opens the "
     "main menu."),
]


MOVES = ("UP", "DOWN", "LEFT", "RIGHT")


def mash_dialogue_steps(rng: "random.Random | None" = None) -> list[Step]:
    """Randomized dialogue advance, generated fresh each invocation so a fixed
    pattern can't get wedged on a particular box, text speed, or yes/no prompt.
    A mostly-A burst (an occasional B guards a mid-burst yes/no stuck on YES)
    that ALWAYS ENDS with one B: the burst cleans up after itself — if its A
    presses surfaced a prompt or menu right at the end, the closing B cancels
    it, so the NEXT decision observes clean dialogue/overworld instead of
    committing blind to whatever the mash left open. (A leading B was tried
    first: it cleans one decision too late — the mess a burst makes is its
    own, not its successor's.) In plain dialogue the trailing B just advances
    text, so it costs nothing. Only A/B here — directions could move or
    menu-cancel wrongly. Short and bursty on purpose: quick taps in rapid
    succession advance text and confirm menus fastest."""
    r = rng or random
    return [Step(button=("B" if r.random() < 0.25 else "A"),
                 hold_frames=r.randint(3, 5), wait_frames=r.randint(4, 9))
            for _ in range(r.randint(4, 8))] + \
           [Step(button="B", hold_frames=r.randint(3, 5),
                 wait_frames=r.randint(4, 9))]


def wander_steps(rng: "random.Random | None" = None) -> list[Step]:
    """A short random walk: head a random direction for a few tiles, maybe turn
    once — so 'fish mode' (and a lost model) explores the map instead of
    jittering on one tile. Movement buttons only. Fresh each call; pass an rng
    to keep a seeded fish reproducible, else module random via step_factory."""
    r = rng or random
    d = r.choice(MOVES)
    steps = [Step(button=d, hold_frames=8, wait_frames=8)
             for _ in range(r.randint(2, 5))]
    if r.random() < 0.4:  # occasional turn so it doesn't only go one way
        d2 = r.choice([m for m in MOVES if m != d])
        steps += [Step(button=d2, hold_frames=8, wait_frames=8)
                  for _ in range(r.randint(1, 3))]
    return steps


def mash_button_steps(button: str, rng: "random.Random | None" = None) -> list[Step]:
    """Press one button several times (commit to a direction, or mash B/A)."""
    r = rng or random
    return [Step(button=button, hold_frames=r.randint(4, 8),
                 wait_frames=r.randint(8, 16))
            for _ in range(r.randint(3, 6))]


def random_mash_steps(buttons: list[str],
                      rng: "random.Random | None" = None) -> list[Step]:
    """Crazy random presses across ALL buttons — the last-ditch 'get me out of
    here' when the model is wedged in a state it can't exit cleanly (e.g. the
    naming grid). Chaotic on purpose: START may jump to END, B erases/cancels,
    directions move — something usually breaks the stuck state."""
    r = rng or random
    return [Step(button=r.choice(buttons), hold_frames=r.randint(4, 8),
                 wait_frames=r.randint(6, 14))
            for _ in range(r.randint(5, 9))]


def fish_move(buttons: list[str], rng: "random.Random | None" = None) -> Behavior:
    """The fish's repertoire: each call randomly picks ONE randomized macro —
    wander, mash-dialogue, commit to a direction, mash B, or a single random
    button — so pure-random play still does structured things (walk a route,
    clear a speech, back out of a menu) instead of only twitching one button.
    Pass a seeded rng to keep calibration runs reproducible."""
    r = rng or random
    roll = r.random()
    if roll < 0.30:
        return Behavior(name="wander", source="builtin", steps=wander_steps(r))
    if roll < 0.50:
        return Behavior(name="mash_through_dialogue", source="builtin",
                        steps=mash_dialogue_steps(r))
    if roll < 0.64:
        d = r.choice(MOVES)
        return Behavior(name=f"mash_{d}", source="builtin",
                        steps=mash_button_steps(d, r))
    if roll < 0.76:
        return Behavior(name="mash_B", source="builtin",
                        steps=mash_button_steps("B", r))
    if roll < 0.88:
        return Behavior(name="get_unstuck", source="builtin",
                        steps=random_mash_steps(buttons, r))
    b = r.choice(buttons)
    return Behavior(name=f"press_{b}", source="builtin",
                    steps=[Step(button=b, hold_frames=8, wait_frames=8)])


def builtins(buttons: list[str]) -> dict[str, Behavior]:
    lib: dict[str, Behavior] = {
        "wait": _builtin("wait", [Step(op="wait", wait_frames=30)],
                         "stand still a moment (black screens, waiting out "
                         "a person in the way)."),
        # short, bursty taps — quick presses in rapid succession clear dialogue
        # and confirm menus/naming screens faster than long-held/spaced presses
        "mash_a": _builtin("mash_a", [Step(button="A", hold_frames=4, wait_frames=6)] * 6,
                           "several quick A taps - fastest through plain "
                           "text; NEVER on a yes/no that commits (one "
                           "deliberate press there)."),
        # RAM-grounded closed loop (executor op "advance_text"): presses A
        # only while a text box is open, stops when it closes or a choice
        # cursor appears, does nothing at all in the overworld — so it can
        # never re-open a conversation or blind-confirm a yes/no. The old
        # open-loop randomized burst (mash_dialogue_steps) survives only in
        # the fish's repertoire.
        "mash_through_dialogue": _builtin(
            "mash_through_dialogue", [Step(op="advance_text")],
            "start AND clear a conversation with whoever you face: presses "
            "A only while text is open, stops the moment a choice appears "
            "(never answers it). Read its feedback: text closed = move on; "
            "stopped at a choice = answer with ONE press; nothing opened = "
            "no one to talk to. Calling it again while still facing someone "
            "restarts their speech."),
        # explore: a fresh short random walk each run (fish + lost-model use)
        "wander": Behavior(name="wander", steps=wander_steps(),
                           source="builtin", step_factory=wander_steps,
                           description="a short random stroll - only when "
                           "truly lost with no bearing to follow."),
        # escape hatch: crazy random inputs to break out of a wedged state
        "get_unstuck": Behavior(name="get_unstuck",
                                steps=random_mash_steps(buttons), source="builtin",
                                step_factory=lambda: random_mash_steps(buttons),
                                description="wild random inputs - LAST "
                                "resort for a wedged screen nothing else "
                                "answers."),
        "savestate": _builtin("savestate", [Step(op="savestate")],
                              "save a progress snapshot."),
    }
    # navigation macros: registered as stubs so the schema enum knows them;
    # the LOOP swaps in a real BFS path at decision time (harness/navigate.py).
    # The wait stub only runs if no map is available that tick. Counted
    # variants (walk_east_3 = exactly up to 3 tiles east) let the model walk
    # a bearing distance instead of always going as far as possible.
    nav_desc = {
        "walk_to_exit": "walk through the NEAREST door/exit including the "
                        "final doormat step - for LEAVING rooms. Outdoors it "
                        "walks INTO the nearest building: never use it "
                        "outside.",
        "walk_to_counter": "walk to the person behind a counter (nurse, "
                           "clerk) and stop FACING them; if they were off "
                           "screen it only gets closer - call it again.",
        "walk_to_grass": "walk into the nearest tall grass and pace inside "
                         "it - repeat it to hunt wild battles.",
    }
    for nav in ("walk_north", "walk_south", "walk_west", "walk_east",
                "walk_to_exit", "walk_to_counter", "walk_to_grass"):
        lib[nav] = _builtin(nav, [Step(op="wait", wait_frames=8)],
                            nav_desc.get(nav))  # walk_<dir>: family line
        if nav not in ("walk_to_exit", "walk_to_counter", "walk_to_grass"):
            for n in range(1, 10):
                lib[f"{nav}_{n}"] = _builtin(f"{nav}_{n}",
                                             [Step(op="wait", wait_frames=8)])
    for b in buttons:
        lib[f"press_{b}"] = _builtin(f"press_{b}", [Step(button=b)])
    return lib


def load_skills(dirs: list[str | Path], base: Path,
                errors: list[str] | None = None) -> dict[str, Behavior]:
    """Load skill YAMLs. A malformed file is SKIPPED (reported via `errors`),
    never raised — a bad checkpoint-authored skill must not stall the loop."""
    lib: dict[str, Behavior] = {}
    for d in dirs:
        d = base / d
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.yaml")):
            try:
                raw = yaml.safe_load(f.read_text(encoding="utf-8"))
                steps = [Step(**s) for s in raw["steps"]]
                lib[raw["name"]] = Behavior(name=raw["name"], steps=steps,
                                            source="skill",
                                            description=raw.get("description"))
            except Exception as e:  # noqa: BLE001 — quarantine, don't crash
                if errors is not None:
                    errors.append(f"{f.name}: {e}")
    return lib


class BehaviorLibrary:
    def __init__(self, profile_buttons: list[str], skills_dirs: list[str], base: Path):
        self.buttons = profile_buttons
        self.load_errors: list[str] = []
        self._lib = builtins(profile_buttons) | load_skills(skills_dirs, base,
                                                            self.load_errors)

    def get(self, name: str) -> Behavior | None:
        return self._lib.get(name)

    def names(self) -> list[str]:
        return sorted(self._lib)

    def listing(self) -> list[str]:
        """Behavior serving: the allowed-behaviors list IS the documentation.
        One line per behavior with its true description; counted walks and
        single presses collapse to family lines (their members stay in the
        schema enum via names())."""
        counted = re.compile(r"walk_(north|south|west|east)_[1-9]$")
        plain_walk = re.compile(r"walk_(north|south|west|east)$")
        press = re.compile(r"press_[A-Z]+$")
        out = [f"{fam} - {desc}" for fam, desc in FAMILY_LINES]
        for name in sorted(self._lib):
            if counted.fullmatch(name) or press.fullmatch(name) \
                    or plain_walk.fullmatch(name):
                continue  # covered by family lines
            b = self._lib[name]
            out.append(f"{name} - {b.description}" if b.description
                       else name)
        return out

    def reload_skills(self, skills_dirs: list[str], base: Path) -> None:
        """Called by HotSync so checkpoint-authored skills appear live."""
        self.load_errors = []
        self._lib = builtins(self.buttons) | load_skills(skills_dirs, base,
                                                         self.load_errors)
