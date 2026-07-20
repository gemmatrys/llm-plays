"""Executor: runs behaviors at frame rate through a Hands driver.

The only component allowed to touch Hands. Phase 4 adds CV-triggered reflexes here
(interrupt a behavior when the screen demands it); the interface already allows it.
"""
from __future__ import annotations

import time

from .interfaces import Extras, Hands, Unsupported
from .types import Behavior

FRAME_S = 1 / 60


class Executor:
    def __init__(self, hands: Hands, extras: Extras | None, savestate_slot: int = 1):
        self.hands = hands
        self.extras = extras
        self.savestate_slot = savestate_slot

    def execute(self, behavior: Behavior) -> None:
        held: set[str] = set()
        # step_factory lets a behavior generate fresh steps each run (e.g. a
        # randomized dialogue-masher); otherwise its static steps are used.
        steps = (behavior.step_factory() if behavior.step_factory is not None
                 else behavior.steps)
        try:
            for step in steps:
                if step.op == "wait":
                    time.sleep(step.wait_frames * FRAME_S)
                elif step.op == "savestate":
                    self.savestate()
                elif step.op == "keydown" and step.button is not None:
                    self.hands.key_down(step.button)
                    held.add(step.button)
                    time.sleep(step.wait_frames * FRAME_S)
                elif step.op == "keyup" and step.button is not None:
                    self.hands.key_up(step.button)
                    held.discard(step.button)
                    time.sleep(step.wait_frames * FRAME_S)
                elif step.button is not None:
                    self.hands.press(step.button, step.hold_frames)
                    time.sleep((step.hold_frames + step.wait_frames) * FRAME_S)
        finally:
            # liveness guard: a behavior may never leave keys stuck down —
            # not even if it forgot a keyup, raised, or the plan gets aborted
            for button in held:
                self.hands.key_up(button)

    def savestate(self) -> bool:
        """Ratchet primitive. Returns False when the platform can't savestate
        (console) — the loop then falls back to the profile's in-game save behavior."""
        if self.extras is None:
            return False
        try:
            self.extras.savestate(self.savestate_slot)
            return True
        except Unsupported:
            return False
