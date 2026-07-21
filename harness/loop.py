"""The main decision loop: ties eyes, watchdog, executor, ratchet, stuckness,
and logging together. This is invariants I1–I3 in motion.
"""
from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from . import navigate
from .behaviors import random_mash_steps
from .executor import Executor
from .interfaces import Extras, Eyes, Unsupported
from .profile import GameProfile
from .runlog import RunLog
from .stream import StreamState
from .stuckness import StucknessMonitor
from .tilemap import TerrainTable, render_ascii
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
        tm = profile.tilemap
        self._terrain = TerrainTable(base / tm.tiles_file) \
            if tm is not None and tm.tiles_file else None
        self._tiles_err: str | None = None
        self._recent: list[str] = []
        self._last_ram: dict[str, int] = {}
        self._last_moved = False  # last decision tried to walk somewhere
        self._nav: dict | None = None  # this tick's pathfinding inputs
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
        if ram is not None and self._last_ram and self._last_moved and all(
                ram.get(k) == self._last_ram.get(k)
                for k in ("map_id", "pos_x", "pos_y")):
            # explicit wall feedback: the model shouldn't have to infer a
            # failed move from the position numbers
            self._recent.append("[move blocked - position unchanged]")
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

        # context-only RAM (e.g. in_battle): shown to the model and logged,
        # never milestone-tracked — its flapping must not spam metrics
        ram_ctx = ram
        if ram is not None and self.profile.context_ram_map:
            try:
                ram_ctx = {**ram,
                           **self.extras.read_ram(self.profile.context_ram_map)}
            except Exception:  # noqa: BLE001 — context extras are optional
                pass

        obs = Observation(frame=frame, ram=ram_ctx, goals=self.runlog.goals(),
                          recent=self._recent, memory=self.runlog.memory(),
                          tilemap=self._read_tilemap())
        decision = self.watchdog.decide(obs)
        # navigation macros: swap the stub for a real BFS path computed on
        # this tick's map — the model chose a destination, the harness walks
        for i, b in enumerate(decision.behaviors):
            if b.name in navigate.NAV_BEHAVIORS:
                nb = navigate.resolve(b.name, **self._nav) \
                    if self._nav is not None else None
                if nb is not None:
                    decision.behaviors[i] = nb
                else:
                    self._recent.append(f"[{b.name}: no path visible]")
        if decision.memory_update is not None:
            # the model rewrote its own notes; store verbatim, never interpret
            self.runlog.set_memory(decision.memory_update)
        if decision.done_goal is not None:
            # the model reports a numbered goal finished; the harness stamps
            # it [DONE] so finished objectives stop being re-chased
            if self.runlog.mark_goal_done(decision.done_goal):
                self.runlog.log_metric("goal_done", goal=decision.done_goal)
                self._recent.append(f"[goal {decision.done_goal} marked DONE]")

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
            feedback = self.executor.execute(behavior)
            if feedback:
                self._recent.append(feedback)
            executed += 1

        self._recent.extend(b.name for b in decision.behaviors[:executed])
        del self._recent[:-20]
        move_tokens = ("UP", "DOWN", "LEFT", "RIGHT", "wander")
        self._last_moved = any(any(t in b.name for t in move_tokens)
                               for b in decision.behaviors[:executed])
        self.runlog.log_decision(decision, fhash, ram_ctx, time.time() - started,
                                 executed)
        if self.stream is not None:
            display = " → ".join(b.name for b in decision.behaviors[:executed])
            self.stream.push_decision(display, int(decision.rung),
                                      decision.reason, ram_ctx, obs.goals,
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
            tileset = None
            portals: set[int] = set()
            if self._terrain is not None or tm.walkable_by_tileset:
                # walkability is per-tileset: pick the set for the CURRENT
                # tileset; an unconfigured one degrades to the raw-id dump
                tileset = self.extras.read_block(tm.tileset_addr, 1)[0]
                walk: set[int] = set()
                if self._terrain is not None:
                    walk, portals = self._terrain.lookup(tileset)
                    if self._terrain.error and self._terrain.error != self._tiles_err:
                        # a bad checkpoint edit to tiles.yaml must self-report;
                        # the last good table keeps rendering meanwhile
                        self._tiles_err = self._terrain.error
                        self.runlog.log_metric(
                            "tiles_invalid", detail=self._terrain.error[:200])
                        self.runlog.escalate(
                            "tiles_invalid",
                            f"tiles file rejected, last good kept: "
                            f"{self._terrain.error[:200]}")
                    elif not self._terrain.error:
                        self._tiles_err = None
                if not walk and tm.walkable_by_tileset:
                    walk = set(tm.walkable_by_tileset.get(tileset, []))
                tm = replace(tm, walkable=sorted(walk))
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
            # NPCs from the sprite table: they block movement but are invisible
            # in the tile data. Slot 0 is the player; img 0xFF = hidden.
            # Verified live: pixel (x//8, (y+4)//8) is the sprite's top-left
            # screen tile and lands on the block grid (player reads (8,8)).
            npcs = []
            try:
                sd = self.extras.read_block(tm.sprites_addr,
                                            16 * tm.sprites_count)
                for i in range(1, tm.sprites_count):
                    s = sd[16 * i:16 * i + 16]
                    if s[0] == 0 or s[2] == 0xFF:
                        continue
                    col, row = s[6] // 8, (s[4] + 4) // 8
                    if 0 <= col < tm.cols and 0 <= row < tm.rows:
                        npcs.append((col, row))
            except Exception:  # noqa: BLE001 — NPC overlay is a nice-to-have
                npcs = []
            # this tick's pathfinding inputs, consumed if the model picks a
            # navigation macro (walk_north etc.)
            self._nav = {"tiles": raw, "cfg": tm, "walkable": set(tm.walkable),
                         "npcs": npcs, "map_wh": map_wh, "player": player,
                         "warps": warps} if tm.walkable else None
            return render_ascii(raw, tm, player=player, map_wh=map_wh, warps=warps,
                                tileset=tileset, portal_ids=portals, npcs=npcs)
        except Exception:  # noqa: BLE001 — tilemap is a nice-to-have, never fatal
            self._nav = None
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
