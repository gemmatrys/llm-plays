"""Route progress: the harness tells the model which sub-step it is on.

The model cannot reliably map its position to "which stage of the plan am
I in" (user, 2026-07-22) - the same blindness as trajectories, solved the
same way: the harness computes it and hands it over. The run dir's HOT
`route.yaml` declares ordered sub-steps for numbered goals, each with a
condition the harness can CHECK from map data:

    routes:
      19:
        steps:
          - name: reach the street west of the Center
            bearing: the street west of the Center   # waypoint name
            within: 2                                # manhattan tiles
          - name: reach the gym doormat
            bearing: the doormat below the Gym entrance
            within: 0
          - name: stand inside the gym
            place: Pewter Gym                        # the location line

Progress LATCHES: once a step's condition has been met on any decision it
stays done (the forest leg flip-flop lesson - drifting away must not
un-finish a step), and meeting a later step marks every earlier one done
(surviving restarts, where the model may wake mid-route). The rendered
line names each step DONE or YOU ARE ON THIS STEP - in the state-line
vocabulary, no jargon. Judge/CV conditions can slot in later as another
condition type; map data covers routes today.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml


def load(path: str | Path) -> dict[int, list[dict]]:
    """routes.yaml -> {goal_number: [step, ...]}. Broken file -> {}."""
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        out = {}
        for g, spec in (raw.get("routes") or {}).items():
            steps = [s for s in (spec.get("steps") or [])
                     if isinstance(s, dict) and s.get("name")]
            if steps:
                out[int(g)] = steps
        return out
    except Exception:  # noqa: BLE001 — a bad edit must not stop play
        return {}


def current_goal(goals_text: str) -> int | None:
    """Lowest numbered goal not stamped [DONE]."""
    for m in re.finditer(r"^(\d+)\.\s*(\[DONE\])?", goals_text, re.M):
        if not m.group(2):
            return int(m.group(1))
    return None


def step_met(step: dict, ram: dict, waypoints: dict) -> bool:
    """Evaluate one step's condition against live map data."""
    place = step.get("place")
    if place is not None:
        return str(ram.get("place", "")).strip().lower() == \
            str(place).strip().lower()
    bearing = step.get("bearing")
    if bearing is not None:
        wp = waypoints.get(bearing)
        if not wp or wp.get("map") != ram.get("map_id"):
            return False
        if ram.get("pos_x") is None or ram.get("pos_y") is None:
            return False
        d = (abs(wp["x"] - ram["pos_x"]) + abs(wp["y"] - ram["pos_y"]))
        return d <= int(step.get("within", 1))
    return False


def progress(steps: list[dict], ram: dict, waypoints: dict,
             latched: set[int]) -> tuple[set[int], int | None]:
    """Update the latch set; return (latched, current step index or None
    when every step is done). Meeting step N latches 0..N."""
    for i, step in enumerate(steps):
        if step_met(step, ram, waypoints):
            latched.update(range(i + 1))
    for i in range(len(steps)):
        if i not in latched:
            return latched, i
    return latched, None


def render(goal: int, steps: list[dict], current: int | None) -> str:
    """The state line: every step named, DONE or YOU ARE ON THIS STEP."""
    lines = [f"Your route for goal {goal}, tracked for you - earlier DONE "
             "steps never need redoing:"]
    for i, step in enumerate(steps):
        if current is None or i < current:
            tag = "DONE"
        elif i == current:
            tag = "YOU ARE ON THIS STEP"
        else:
            tag = "later"
        lines.append(f"  ({i + 1}) {step['name']} - {tag}")
    if current is None:
        lines.append("  Every step is done - the goal's own DONE line is "
                     "what remains.")
    return "\n".join(lines)
