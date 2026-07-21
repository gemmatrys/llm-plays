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
    def __init__(self, hands: Hands, extras: Extras | None, savestate_slot: int = 1,
                 dialog=None):
        self.hands = hands
        self.extras = extras
        self.savestate_slot = savestate_slot
        self.dialog = dialog  # TilemapConfig (font/cursor fields) or None

    def execute(self, behavior: Behavior) -> str | None:
        """Run the behavior. Returns an optional feedback string for the
        model's recent-actions context (e.g. how a text advance ended)."""
        held: set[str] = set()
        feedback: str | None = None
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
                elif step.op == "advance_text":
                    feedback = self._advance_text()
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
        return feedback

    def _advance_text(self) -> str:
        """Closed-loop dialogue advance (op "advance_text"): press A only
        while a text box is actually open, stop the moment it closes or a
        choice menu appears. RAM-grounded so it can neither re-open a
        conversation by pressing into the overworld nor blind-confirm a
        yes/no — the two failure modes of the old open-loop mash."""
        d = self.dialog
        if self.extras is None or d is None:
            return "[text advance unavailable - no RAM access]"
        for i in range(d.max_text_presses):
            try:
                tiles = self.extras.read_block(d.addr, d.cols * d.rows)
                if d.menu_cursor_tile in tiles:
                    return ("[stopped at a choice/menu - answer it with ONE "
                            "deliberate press]" if i else
                            "[a choice/menu is on screen - answer it with "
                            "ONE deliberate press]")
                in_battle = (self.extras.read_block(d.battle_addr, 1)[0]
                             if d.battle_addr is not None else 0)
                if not in_battle:
                    # overworld: wFontLoaded bit 0 is the text-box truth
                    font = self.extras.read_block(d.font_addr, 1)[0]
                    if not (font & 1):
                        return (f"[text closed after {i} presses]" if i else
                                "[no text box is open - nothing pressed]")
                # in battle there is no font flag (battles never set it):
                # press through result text until the menu cursor shows up
                # or the battle ends (the not-in-battle branch then closes)
            except Exception:  # noqa: BLE001 — degrade loud, not wedged
                return "[text advance aborted - RAM read failed]"
            self.hands.press("A", 4)
            time.sleep((4 + 24) * FRAME_S)
        return f"[text still open after {d.max_text_presses} presses]"

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
