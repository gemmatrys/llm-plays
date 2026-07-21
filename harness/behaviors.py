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
from pathlib import Path

import yaml

from .types import Behavior, Step


def _builtin(name: str, steps: list[Step]) -> Behavior:
    return Behavior(name=name, steps=steps, source="builtin")


MOVES = ("UP", "DOWN", "LEFT", "RIGHT")


def mash_dialogue_steps(rng: "random.Random | None" = None) -> list[Step]:
    """Randomized dialogue advance, generated fresh each invocation so a fixed
    pattern can't get wedged on a particular box, text speed, or yes/no prompt.
    ALWAYS leads with one B: it pre-empts whatever the previous action left
    open — cancels a menu, answers NO to a yes/no sitting on YES — before any
    A can commit to it, and in plain dialogue B advances text just like A, so
    the pre-empt costs nothing. Then a mostly-A burst (an occasional B keeps
    guarding mid-burst); count and pacing vary. Only A/B here — directions
    could move/menu-cancel wrongly. Short and bursty on purpose: quick taps in
    rapid succession advance text and confirm menus fastest."""
    r = rng or random
    return [Step(button="B", hold_frames=r.randint(3, 5),
                 wait_frames=r.randint(4, 9))] + \
           [Step(button=("B" if r.random() < 0.25 else "A"),
                 hold_frames=r.randint(3, 5), wait_frames=r.randint(4, 9))
            for _ in range(r.randint(4, 8))]


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
        "wait": _builtin("wait", [Step(op="wait", wait_frames=30)]),
        # short, bursty taps — quick presses in rapid succession clear dialogue
        # and confirm menus/naming screens faster than long-held/spaced presses
        "mash_a": _builtin("mash_a", [Step(button="A", hold_frames=4, wait_frames=6)] * 6),
        # randomized each run via step_factory (see mash_dialogue_steps)
        "mash_through_dialogue": Behavior(
            name="mash_through_dialogue", steps=mash_dialogue_steps(),
            source="builtin", step_factory=mash_dialogue_steps),
        # explore: a fresh short random walk each run (fish + lost-model use)
        "wander": Behavior(name="wander", steps=wander_steps(),
                           source="builtin", step_factory=wander_steps),
        # escape hatch: crazy random inputs to break out of a wedged state
        "get_unstuck": Behavior(name="get_unstuck",
                                steps=random_mash_steps(buttons), source="builtin",
                                step_factory=lambda: random_mash_steps(buttons)),
        "savestate": _builtin("savestate", [Step(op="savestate")]),
    }
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
                                            source="skill")
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

    def reload_skills(self, skills_dirs: list[str], base: Path) -> None:
        """Called by HotSync so checkpoint-authored skills appear live."""
        self.load_errors = []
        self._lib = builtins(self.buttons) | load_skills(skills_dirs, base,
                                                         self.load_errors)
