"""The fish: uniform random button presses. Baseline and calibration policy.

Kept as a *policy* (not just the watchdog's rung 4) so calibration mode can run it
as the primary decision source and measure baseline progress-per-hour.
"""
from __future__ import annotations

import random

from ..behaviors import fish_move
from ..types import Behavior, Observation


class FishPolicy:
    name = "fish"

    def __init__(self, buttons: list[str], seed: int | None = None):
        self.buttons = buttons
        self._rng = random.Random(seed)
        self.last_reason = "blub"  # shown on the stream overlay; fish are laconic

    def decide(self, obs: Observation) -> Behavior:
        # a randomized macro from the fish repertoire (wander / mash-dialogue /
        # mash-direction / mash-B / press-any); seeded rng keeps calibration
        # runs reproducible. The behavior name doubles as the overlay reason.
        move = fish_move(self.buttons, self._rng)
        self.last_reason = move.name
        return move
