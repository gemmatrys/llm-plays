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

from pathlib import Path

import yaml

from .types import Behavior, Step


def _builtin(name: str, steps: list[Step]) -> Behavior:
    return Behavior(name=name, steps=steps, source="builtin")


def builtins(buttons: list[str]) -> dict[str, Behavior]:
    lib: dict[str, Behavior] = {
        "wait": _builtin("wait", [Step(op="wait", wait_frames=30)]),
        "mash_a": _builtin("mash_a", [Step(button="A", hold_frames=6, wait_frames=10)] * 4),
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
