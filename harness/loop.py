"""The main decision loop: ties eyes, watchdog, executor, ratchet, stuckness,
and logging together. This is invariants I1–I3 in motion.
"""
from __future__ import annotations

import time
from pathlib import Path

from .behaviors import random_mash_steps
from .executor import Executor
from .interfaces import Extras, Eyes, Unsupported
from .profile import GameProfile
from .runlog import RunLog
from .stream import StreamState
from .stuckness import StucknessMonitor
from .tilemap import render_ascii
from .types import Behavior, Observation, phash_diff


class GameLoop:
    def __init__(self, profile: GameProfile, eyes: Eyes, executor: Executor,
                 extras: Extras | None, watchdog, runlog: RunLog, base: Path,
                 stream: StreamState | None = None, sync=None):
        self.profile = profile
        self.eyes = eyes
        self.executor = executor
        self.extras = extras
        self.watchdog = watchdog
        self.runlog = runlog
        self.base = base
        self.stream = stream
        self.sync = sync
        self.stuckness = StucknessMonitor(profile.escalation)
        self._recent: list[str] = []
        self._last_ram: dict[str, int] = {}
        self._last_save_ts = 0.0
        self._last_snapshot_ts = 0.0

    def run(self, max_iterations: int | None = None) -> None:
        i = 0
        consecutive_errors = 0
        while max_iterations is None or i < max_iterations:
            i += 1
            started = time.time()
            try:
                self._tick()
                consecutive_errors = 0
            except KeyboardInterrupt:
                break
            except Exception as e:  # noqa: BLE001 — the loop must survive anything
                self.runlog.log_metric("tick_error", error=repr(e))
                consecutive_errors += 1
                if consecutive_errors == 5:
                    # eyes/hands are down (emulator killed, bridge gone) —
                    # scream once instead of quietly erroring forever
                    self.runlog.escalate(
                        "driver_down",
                        f"{consecutive_errors} consecutive tick errors; latest: {e!r}")
                    if self.stream is not None:
                        self.stream.bump("escalations")
                time.sleep(min(2.0 * consecutive_errors, 15.0))
                continue
            # pace to the profile's decision cadence
            remaining = self.profile.decision_cadence_s - (time.time() - started)
            if remaining > 0:
                time.sleep(remaining)
        self.runlog.close()

    def _tick(self) -> None:
        started = time.time()
        if self.sync is not None:
            changed = self.sync.poll()  # checkpoint-authored skills go live here
            if changed:
                self.runlog.log_metric("skills_sync", files=changed)
                errs = self.sync.library.load_errors
                if errs:
                    # a bad write must self-report, not silently vanish
                    self.runlog.log_metric("skills_invalid", errors=errs)
                    self.runlog.escalate(
                        "skills_invalid",
                        f"skill files rejected and skipped: {'; '.join(errs)}")
        frame = self.eyes.get_frame()
        fhash = frame.phash()

        ram = None
        if self.extras is not None and self.profile.ram_map:
            try:
                ram = self.extras.read_ram(self.profile.ram_map)
            except Unsupported:
                pass
        if ram is not None and ram != self._last_ram:
            changed = {k: v for k, v in ram.items() if self._last_ram.get(k) != v}
            if "map_id" in changed and self._last_ram:
                # visible in the model's recent-actions context: bouncing
                # between two maps = walking into a door, and now it can see it
                self._recent.append(f"[entered map {ram['map_id']}]")
            if any(k not in ("pos_x", "pos_y") for k in changed):
                # milestone events (badge gained, map changed, ...) — raw
                # material for the progress curves; position isn't a milestone
                marks = {k: v for k, v in changed.items()
                         if k not in ("pos_x", "pos_y")}
                self.runlog.log_metric("milestone", **marks)
                self.runlog.snapshot(frame, tag="milestone")
                self.stuckness.note_milestone()
            self._last_ram = ram

        obs = Observation(frame=frame, ram=ram, goals=self.runlog.goals(),
                          recent=self._recent, memory=self.runlog.memory(),
                          tilemap=self._read_tilemap())
        decision = self.watchdog.decide(obs)
        if decision.memory_update is not None:
            # the model rewrote its own notes; store verbatim, never interpret
            self.runlog.set_memory(decision.memory_update)

        # Execute the plan; abort remaining steps if the screen changes more than
        # expected between steps (wild encounter, dialogue popup, scene change).
        executed = 0
        prev_hash = fhash
        for i, behavior in enumerate(decision.behaviors):
            if i > 0:
                cur_hash = self.eyes.get_frame().phash()
                if phash_diff(prev_hash, cur_hash) > self.profile.ladder.plan_abort_pct:
                    self.runlog.log_metric("plan_abort", step=i,
                                           total=len(decision.behaviors))
                    break
                prev_hash = cur_hash
            self.executor.execute(behavior)
            executed += 1

        self._recent.extend(b.name for b in decision.behaviors[:executed])
        del self._recent[:-20]
        self.runlog.log_decision(decision, fhash, ram, time.time() - started, executed)
        if self.stream is not None:
            display = " → ".join(b.name for b in decision.behaviors[:executed])
            self.stream.push_decision(display, int(decision.rung),
                                      decision.reason, ram, obs.goals,
                                      memory=self.runlog.memory(),
                                      thinking=decision.thinking)

        self._ratchet()
        self._watch_stuckness(frame, fhash, ram,
                              [b.name for b in decision.behaviors[:executed]])
        self._periodic_snapshot(frame)

    def _read_tilemap(self) -> str:
        """Bulk-read the screen tilemap + map dims + warps and render an ASCII
        walkability map with blocked borders and marked exits. Fully optional:
        no tilemap config, a console driver without read_block, or an old Lua
        bridge lacking READBLOCK all degrade to "" — the harness must run
        identically with or without this context."""
        tm = self.profile.tilemap
        if tm is None or self.extras is None or not hasattr(self.extras, "read_block"):
            return ""
        try:
            raw = self.extras.read_block(tm.addr, tm.cols * tm.rows)
            px, py = self._last_ram.get("pos_x"), self._last_ram.get("pos_y")
            player = (px, py) if px is not None and py is not None else None
            # map size (blocks -> tiles) so off-map tiles render blocked
            hw = self.extras.read_block(tm.height_addr, 2)  # [height, width] blocks
            map_wh = (hw[1] * 2, hw[0] * 2)
            # warps: doors/stairs/holes. Gen 1 stores each entry y-FIRST
            # (y, x, destWarp, destMap) — confirmed by walking onto one — so the
            # map tile is (x = byte1, y = byte0).
            n = self.extras.read_block(tm.warp_count_addr, 1)[0]
            warps = []
            if n:
                wb = self.extras.read_block(tm.warp_entry_addr, 4 * min(n, 32))
                warps = [(wb[4 * i + 1], wb[4 * i]) for i in range(min(n, 32))]
            return render_ascii(raw, tm, player=player, map_wh=map_wh, warps=warps)
        except Exception:  # noqa: BLE001 — tilemap is a nice-to-have, never fatal
            return ""

    # -- invariant I2: progress ratchet --------------------------------------
    def _ratchet(self) -> None:
        if time.time() - self._last_save_ts < self.profile.ratchet.interval_s:
            return
        if self.executor.savestate():
            self.runlog.log_metric("savestate", slot=self.profile.ratchet.savestate_slot)
            if self.stream is not None:
                self.stream.bump("savestates")
        elif self.profile.ratchet.ingame_save_behavior:
            b = self.watchdog.library.get(self.profile.ratchet.ingame_save_behavior)
            if b:
                self.executor.execute(b)
                self.runlog.log_metric("ingame_save", behavior=b.name)
        self._last_save_ts = time.time()

    # -- invariant I3: bounded stuckness --------------------------------------
    def _watch_stuckness(self, frame, fhash: str, ram: dict | None,
                         executed: list[str]) -> None:
        self.stuckness.observe(fhash, ram, executed)
        reasons = self.stuckness.stuck_reasons()
        if not reasons:
            return
        response = self.stuckness.next_response(reasons,
                                                self.profile.ladder.allow_random)
        if response == "wait":  # a rescue is still inside its grace period
            return
        if response == "rescue":
            # first response is mechanical: one bounded random-input burst (the
            # same get_unstuck escape the model can pick) before spending a wake
            self.runlog.log_metric("self_rescue", signals=reasons)
            self.executor.execute(Behavior(
                name="get_unstuck", source="builtin",
                steps=random_mash_steps(self.profile.buttons)))
            return
        snap = self.runlog.snapshot(frame, tag="stuck")
        if self.stuckness.may_wake_claude():
            self.runlog.escalate("stuck",
                                 f"stuck signals: {', '.join(reasons)}", snap)
            self.runlog.log_metric("escalation", reason="stuck", signals=reasons)
            if self.stream is not None:
                self.stream.bump("escalations")
            try:
                # an early-woken Claude should find a fresh context bundle
                from .briefing import write_briefing
                write_briefing(self.runlog.dir)
            except Exception as e:  # noqa: BLE001 — briefing must never kill the loop
                self.runlog.log_metric("briefing_error", error=repr(e))
        else:
            self.runlog.log_metric("escalation_suppressed", reason="stuck",
                                   signals=reasons)
        self.stuckness.reset()

    def _periodic_snapshot(self, frame, every_s: float = 600.0) -> None:
        if time.time() - self._last_snapshot_ts > every_s:
            self.runlog.snapshot(frame)
            self._last_snapshot_ts = time.time()
