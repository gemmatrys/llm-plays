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
                 dialog=None, eyes=None, ram_map: dict | None = None):
        self.hands = hands
        self.extras = extras
        self.savestate_slot = savestate_slot
        self.dialog = dialog  # TilemapConfig (font/cursor fields) or None
        self.eyes = eyes  # for op "verify" screenshots; None = no judge calls
        self.ram_map = ram_map or {}  # profile ram_map, for verify tripwires
        # the JUDGE (op "verify"): callable(frame, expect) -> (matches, seen),
        # wired by cli to LLMPolicy.verify when the llm policy runs
        self.judge = None
        self.on_verify = None  # callable(**kw), wired to runlog.log_metric

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
                elif step.op == "verify":
                    v = self._verify(step)
                    if v is not None:  # only failures speak; success is silent
                        feedback = v
                        if step.abort_on_fail:
                            # checkpoint says wrong screen: remaining steps
                            # would fire blind - stop, tell the model what
                            # the judge actually saw
                            feedback = f"[{behavior.name} stopped - " + v[1:]
                            break
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
        pressed = 0
        saw_text = False
        for _ in range(d.max_text_presses):
            try:
                tiles = self.extras.read_block(d.addr, d.cols * d.rows)
                if d.menu_cursor_tile in tiles:
                    # the ONE state that never gets a blind press: a visible
                    # choice cursor — an A here commits irreversibly
                    return ("[stopped at a choice/menu - answer it with ONE "
                            "deliberate press]" if pressed else
                            "[a choice/menu is on screen - answer it with "
                            "ONE deliberate press]")
                in_battle = (self.extras.read_block(d.battle_addr, 1)[0]
                             if d.battle_addr is not None else 0)
                # battles never set wFontLoaded — in battle, "text open"
                # until the menu cursor shows or the battle ends
                text_open = bool(in_battle) or bool(
                    self.extras.read_block(d.font_addr, 1)[0] & 1)
                saw_text = saw_text or text_open
                if not text_open and pressed:
                    # ALWAYS press at least once (universal rule: text-state
                    # flags have per-mode blind spots, and the first A also
                    # STARTS a conversation with whoever is faced) — then
                    # stop the moment the follow-through sees it closed
                    return (f"[text closed after {pressed} presses]"
                            if saw_text else
                            "[pressed A once - nothing opened]")
            except Exception:  # noqa: BLE001 — degrade loud, not wedged
                return "[text advance aborted - RAM read failed]"
            self.hands.press("A", 4)
            pressed += 1
            time.sleep((4 + 24) * FRAME_S)
        return f"[text still open after {pressed} presses]"

    def _verify(self, step) -> str | None:
        """Tripwire-judge step validation (op "verify"). The tripwire is a
        cheap engine-bit read that decides WHETHER to ask - it never rules on
        truth itself. The judge (the LLM, looking at the settled screen) is
        the sole authority on what actually happened; the common success path
        costs nothing. Returns None on pass, loud feedback on fail/unavailable
        (fail open - a broken verify must not wedge the loop)."""
        expect = step.expect or "the expected screen"
        trip = step.tripwire
        if trip and self.extras is not None:
            addr = self.ram_map.get(trip.get("field"))
            if addr is not None:
                try:
                    field = trip["field"]
                    val = self.extras.read_ram({field: addr})[field]
                    if val == trip.get("equals"):
                        self._verify_metric(expect, verdict="tripwire_pass")
                        return None  # engine bit confirms - no judgment needed
                except Exception:  # noqa: BLE001 — tripwire down -> summon judge
                    pass
        if self.judge is None or self.eyes is None:
            self._verify_metric(expect, verdict="no_judge")
            return f"[verify: could not confirm - {expect}]"
        self._verify_metric(expect, verdict="judging")  # overlay-only beat
        time.sleep(step.wait_frames * FRAME_S)  # let the screen settle
        try:
            matches, seen = self.judge(self.eyes.get_frame(), expect)
        except Exception as e:  # noqa: BLE001
            self._verify_metric(expect, verdict="judge_error", detail=str(e)[:120])
            return f"[verify unavailable - could not confirm: {expect}]"
        self._verify_metric(expect, verdict="match" if matches else "mismatch",
                            seen=seen)
        if matches:
            return None
        return f"[verify FAILED: expected {expect}; the screen shows: {seen}]"

    def _verify_metric(self, expect: str, **kw) -> None:
        if self.on_verify is not None:
            try:
                self.on_verify(expect=expect, **kw)
            except Exception:  # noqa: BLE001 — metrics must never break play
                pass

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
