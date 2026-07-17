"""The fish: uniform random button presses. Baseline and calibration policy.

Kept as a *policy* (not just the watchdog's rung 4) so calibration mode can run it
as the primary decision source and measure baseline progress-per-hour.
"""
from __future__ import annotations

import random

from ..types import Behavior, Observation, Step


class FishPolicy:
    name = "fish"

    def __init__(self, buttons: list[str], seed: int | None = None):
        self.buttons = buttons
        self._rng = random.Random(seed)
        self.last_reason = "blub"  # shown on the stream overlay; fish are laconic

    def decide(self, obs: Observation) -> Behavior:
        button = self._rng.choice(self.buttons)
        return Behavior(name=f"press_{button}", source="builtin",
                        steps=[Step(button=button, hold_frames=8, wait_frames=8)])
