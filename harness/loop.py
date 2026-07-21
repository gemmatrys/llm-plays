"""The main decision loop: ties eyes, watchdog, executor, ratchet, stuckness,
and logging together. This is invariants I1–I3 in motion.
"""
from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import yaml

from . import navigate
from .behaviors import random_mash_steps
from .executor import Executor
from .interfaces import Extras, Eyes, Unsupported
from .profile import GameProfile
from .runlog import RunLog
from .stream import StreamState
from .stuckness import StucknessMonitor
from .tilemap import TerrainTable, _map_coord, render_ascii
from .types import Behavior, Observation, Step, phash_diff


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
        # notes-staleness tracking: map the notes were last rewritten on and
        # decisions since — feeds the forced-"memory" schema (policy/llm.py)
        self._notes_map: int | None = None
        self._notes_age = 0
        # verified-inventory + repeated-structure state
        self._last_bag: dict[int, int] | None = None
        self._map_visits: dict[int, int] = {}
        self._items_cache: tuple[float, dict[int, str]] | None = None
        self._moves_cache: tuple[float, dict[int, str]] | None = None
        self._wp_cache: tuple[float, dict] | None = None
        self._maps_cache: tuple[float, dict[int, str]] | None = None
        self._goals_alarmed = False  # latch for the all-goals-done escalation
        self._nav: dict | None = None  # this tick's pathfinding inputs
        self._grass_seen: dict[int, tuple[int, int]] = {}  # map_id -> map (x,y)
        self._nav_blocked = 0  # consecutive walk-attempts with zero movement
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
        # settle before snapshotting: a warp/edge crossing caught
        # mid-animation yields a torn map/pos pair (map 41 with street
        # coords was logged live) and a fade frame. Re-read every 0.5s
        # until two consecutive reads agree on map/pos, then grab the
        # frame - so bearings, place= and the screenshot all describe
        # the same settled state. Capped; the cadence floor absorbs it.
        ram = None
        if self.extras is not None and self.profile.ram_map:
            try:
                ram = self.extras.read_ram(self.profile.ram_map)
                for _ in range(6):
                    time.sleep(0.5)
                    again = self.extras.read_ram(self.profile.ram_map)
                    settled = all(again.get(k) == ram.get(k)
                                  for k in ("map_id", "pos_x", "pos_y"))
                    ram = again
                    if settled:
                        break
            except Unsupported:
                pass
        frame = self.eyes.get_frame()
        fhash = frame.phash()
        prev_ram = self._last_ram  # pre-update snapshot for the move checks
        if ram is not None and ram != self._last_ram:
            changed = {k: v for k, v in ram.items() if self._last_ram.get(k) != v}
            if "map_id" in changed and self._last_ram:
                # visible in the model's recent-actions context: bouncing
                # between two maps = walking into a door, and now it can see it
                self._recent.append(f"[entered map {ram['map_id']}]")
                # repeated-structure counter: the model cannot infer "I keep
                # coming back here" from a 20-item action list, so count for it
                n = self._map_visits.get(ram["map_id"], 0) + 1
                self._map_visits[ram["map_id"]] = n
                if n >= 3:
                    self._recent.append(
                        f"[you have entered this map {n} times - if you are "
                        "not making progress here, your belief about this "
                        "place is probably wrong]")
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

        # wall feedback + walk-effectiveness watchdog — AFTER the battle
        # flag is known: in battle the position is frozen by design and
        # menu presses (DOWN to EMBER) look like movement attempts, which
        # false-fired nav_ineffective mid-Kakuna-fight on 2026-07-21
        in_battle_now = bool((ram_ctx or {}).get("in_battle"))
        if in_battle_now:
            self._nav_blocked = 0
        elif ram is not None and prev_ram and self._last_moved and all(
                ram.get(k) == prev_ram.get(k)
                for k in ("map_id", "pos_x", "pos_y")):
            # explicit wall feedback: the model shouldn't have to infer a
            # failed move from the position numbers
            self._recent.append("[move blocked - position unchanged]")
            # walks that repeatedly move the player ZERO tiles mean the
            # walkability data lies about this spot (the gate-doorway
            # wedge) — escalate WITH the raw block ids so the checkpoint
            # can fix tiles.yaml without spelunking
            self._nav_blocked += 1
            if self._nav_blocked == 3:
                detail = (f"walks not moving the player: map "
                          f"{ram.get('map_id')} pos "
                          f"({ram.get('pos_x')},{ram.get('pos_y')})")
                if self._nav is not None:
                    t, cfg = self._nav["tiles"], self._nav["cfg"]
                    pc, pr = cfg.player_col // 2, cfg.player_row // 2
                    ids = {}
                    for lbl, dc, dr in (("N", 0, -1), ("S", 0, 1),
                                        ("W", -1, 0), ("E", 1, 0),
                                        ("here", 0, 0)):
                        bc, br = pc + dc, pr + dr
                        if 0 <= bc < cfg.cols // 2 and 0 <= br < cfg.rows // 2:
                            ids[lbl] = f"0x{t[(br * 2 + 1) * cfg.cols + bc * 2]:02x}"
                    detail += f"; neighbor block ids {ids}"
                self.runlog.log_metric("nav_ineffective")
                self.runlog.escalate("nav_ineffective", detail)
        elif ram is not None and prev_ram and any(
                ram.get(k) != prev_ram.get(k)
                for k in ("map_id", "pos_x", "pos_y")):
            self._nav_blocked = 0

        # bag = game-VERIFIED inventory in the model's {ram} view, plus delta
        # events. Beliefs like "I should have the parcel now" die against a
        # displayed "bag=(empty)"; item gains/losses are the ground-truth
        # spine that self-narrated events ("I healed", "I delivered") lack.
        if ram_ctx is not None and self.profile.bag is not None \
                and self.extras is not None:
            try:
                bag = self._read_bag()
                names = self._item_names()
                ram_ctx = dict(ram_ctx)
                ram_ctx["bag"] = ", ".join(
                    f"{names.get(i, f'ITEM_0x{i:02x}')} x{q}"
                    for i, q in bag.items()) or "(empty)"
                if self._last_bag is not None and bag != self._last_bag:
                    for i in set(bag) | set(self._last_bag):
                        d = bag.get(i, 0) - self._last_bag.get(i, 0)
                        if d:
                            nm = names.get(i, f"ITEM_0x{i:02x}")
                            self._recent.append(
                                f"[bag: {'+' if d > 0 else ''}{d} {nm} "
                                "(game-verified)]")
                self._last_bag = bag
            except Exception:  # noqa: BLE001 — bag context is optional
                pass

        # live compass: bearings to checkpoint-curated waypoints (HOT file in
        # the run dir), recomputed from the true position every decision — so
        # goal text never carries compass directions that rot as the player
        # moves (a "the Mart is west of you" note is wrong three walks later)
        if ram_ctx is not None and {"map_id", "pos_x", "pos_y"} <= ram_ctx.keys():
            b = self._bearings(ram_ctx)
            if b:
                ram_ctx = dict(ram_ctx)
                ram_ctx["bearings"] = b

        # place name: interiors all look alike to the model (it has called a
        # house the Center, a house the Mart, and the lab both) — the harness
        # KNOWS the map id, so say it by name (HOT data/<game>/maps.yaml,
        # live-verified ids only; unlisted ids self-tag as unknown)
        if ram_ctx is not None and "map_id" in ram_ctx:
            names = self._map_names()
            ram_ctx = dict(ram_ctx)
            ram_ctx["place"] = names.get(
                ram_ctx["map_id"], f"map {ram_ctx['map_id']} (unknown)")

        # money = the third resource goals reason about (buying, the
        # blackout halving) — 3-byte BCD; goals said "if money is short"
        # to a model that could not see money (2026-07-21 audit)
        if ram_ctx is not None and self.profile.party is not None \
                and self.profile.party.money_addr is not None \
                and self.extras is not None:
            try:
                mb = self.extras.read_block(self.profile.party.money_addr, 3)
                ram_ctx = dict(ram_ctx)
                ram_ctx["money"] = int("".join(f"{b:02x}" for b in mb))
            except Exception:  # noqa: BLE001 — money context is optional
                pass

        # party = the team's REAL state (nick, species, level, HP, status):
        # the model must see "HP 4/24" and "POISONED" to decide to heal —
        # asking it to remember battle outcomes is how false beliefs start
        if ram_ctx is not None and self.profile.party is not None \
                and self.extras is not None:
            try:
                p = self._read_party()
                if p:
                    ram_ctx = dict(ram_ctx)
                    ram_ctx["party"] = p
            except Exception:  # noqa: BLE001 — party context is optional
                pass

        # battle hint: enemy identity + Gen 1 type math, computed — a 31B
        # shouldn't burn thinking tokens deriving that Ember is resisted by
        # a Geodude when a lookup table knows it cold
        if ram_ctx is not None and ram_ctx.get("in_battle") \
                and self.profile.battle is not None and self.extras is not None:
            try:
                h = self._battle_hint()
                if h:
                    ram_ctx = dict(ram_ctx)
                    ram_ctx["battle_hint"] = h
            except Exception:  # noqa: BLE001 — hint is optional context
                pass

        # stale notes: the model keeps acting on a world description it wrote
        # rooms ago (this repeatedly cost progress). When its notes predate a
        # map change or sit unchanged too long, tell the policy to FORCE a
        # rewrite (the "memory" field becomes schema-required). Never mid-
        # battle — battle screens are the wrong moment to describe the world.
        map_now = (ram or {}).get("map_id")
        if self._notes_map is None:
            self._notes_map = map_now
        stale = None
        if map_now is not None and not (ram_ctx or {}).get("in_battle"):
            if map_now != self._notes_map:
                stale = "you have moved to a different map since writing them"
            elif self._notes_age >= 15:
                stale = f"unchanged for {self._notes_age} decisions"

        obs = Observation(frame=frame, ram=ram_ctx, goals=self.runlog.goals(),
                          recent=self._recent, memory=self.runlog.memory(),
                          tilemap=self._read_tilemap(),
                          extra={"stale_notes": stale} if stale else {})
        decision = self.watchdog.decide(obs)
        # navigation macros: swap the stub for a real BFS path computed on
        # this tick's map — the model chose a destination, the harness walks
        for i, b in enumerate(decision.behaviors):
            if navigate.is_nav(b.name):
                nb = navigate.resolve(b.name, **self._nav) \
                    if self._nav is not None else None
                if nb is not None:
                    decision.behaviors[i] = nb
                    continue
                base, _n = navigate.parse(b.name)
                btn = {"walk_north": "UP", "walk_south": "DOWN",
                       "walk_west": "LEFT", "walk_east": "RIGHT"}.get(base)
                if btn is not None:
                    # directional walks NEVER dead-end silently: with no
                    # walkable map this tick (unharvested tileset, tilemap
                    # read failure) fall back to ONE direct press — it
                    # still turns/steps, and "[move blocked]" reports a
                    # real wall (the gate-building wedge of 2026-07-21)
                    decision.behaviors[i] = Behavior(
                        name=b.name, source="builtin",
                        steps=[Step(button=btn, hold_frames=16,
                                    wait_frames=8)])
                    self._recent.append(
                        f"[{b.name}: area not mapped - pressed {btn} once]")
                elif b.name == "walk_to_grass":
                    # distinct from a routing failure: nothing to route TO
                    self._recent.append(
                        "[walk_to_grass: no grass in sight on this map - "
                        "it may have none; move on]")
                else:
                    self._recent.append(f"[{b.name}: no path visible]")
        if decision.memory_update is not None:
            # the model rewrote its own notes; store verbatim, never interpret
            self.runlog.set_memory(decision.memory_update)
            self._notes_map = map_now
            self._notes_age = 0
        else:
            self._notes_age += 1
        if decision.done_goal is not None:
            # the model reports a numbered goal finished; the harness stamps
            # it [DONE] so finished objectives stop being re-chased
            if self.runlog.mark_goal_done(decision.done_goal):
                self.runlog.log_metric("goal_done", goal=decision.done_goal)
                self._recent.append(f"[goal {decision.done_goal} marked DONE]")

        # out of objectives: ALARM once (toast + checkpoint wake), don't
        # silently idle — the model wanders on a finished list. Trigger is
        # the LAST numbered goal being stamped (instruction-style middle
        # goals never earn stamps). Latched; a rewrite with a fresh final
        # goal re-arms it. Catches both the model stamping it AND a
        # checkpoint writing a finished file.
        if self.runlog.goals_finished():
            if not self._goals_alarmed:
                self._goals_alarmed = True
                self.runlog.log_metric("goals_finished")
                self.runlog.escalate(
                    "goals_complete",
                    "the last numbered goal is stamped [DONE] - write the "
                    "next goals; the model is idling on a finished list")
                self._recent.append(
                    "[GOALS COMPLETE - new goals are being written; stay "
                    "where you are, do not wander]")
        else:
            self._goals_alarmed = False

        # Execute the plan; abort remaining steps if the screen changes more than
        # expected between steps (wild encounter, dialogue popup, scene change).
        executed = 0
        prev_hash = fhash
        expect_choice = False
        for i, behavior in enumerate(decision.behaviors):
            if i > 0:
                cur_hash = self.eyes.get_frame().phash()
                if (not expect_choice and phash_diff(prev_hash, cur_hash)
                        > self.profile.ladder.plan_abort_pct):
                    self.runlog.log_metric("plan_abort", step=i,
                                           total=len(decision.behaviors))
                    break
                prev_hash = cur_hash
            expect_choice = False
            feedback = self.executor.execute(behavior)
            if feedback:
                self._recent.append(feedback)
            executed += 1
            if feedback and "choice/menu" in feedback:
                # advance_text stopped at a live choice cursor. The ONE
                # deliberate press answering it may be the very next planned
                # step (press_A/press_B) - let that run, and shield it from
                # the phash abort (the menu popping IS the expected screen
                # change). ANY other follow-up is presses written for a world
                # without this menu (a walk's arrows move the cursor onto
                # NO - this silently cancelled a nurse heal): abort and hand
                # the choice back to a fresh decision, cursor untouched.
                nxt = (decision.behaviors[i + 1].name
                       if i + 1 < len(decision.behaviors) else None)
                if nxt in ("press_A", "press_B"):
                    expect_choice = True
                else:
                    if nxt is not None:
                        self.runlog.log_metric("plan_abort", step=i + 1,
                                               total=len(decision.behaviors),
                                               why="choice_cursor")
                    break

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

    def _read_bag(self) -> dict[int, int]:
        """Read the bag as {item_id: qty} (Gen 1: count byte + (id,qty)
        pairs). Caller guards profile.bag/extras and catches errors."""
        bc = self.profile.bag
        n = min(self.extras.read_block(bc.count_addr, 1)[0], bc.max_items)
        if not n:
            return {}
        raw = self.extras.read_block(bc.items_addr, 2 * n)
        return {raw[2 * i]: raw[2 * i + 1] for i in range(n)}

    def _item_names(self) -> dict[int, str]:
        """HOT id->name table (data/<game>/items.yaml, same checkpoint-harvest
        pattern as tiles.yaml). Unknown ids display as ITEM_0xXX — a tag the
        checkpoint sees in logs and names once identified."""
        bc = self.profile.bag
        if bc.names_file is None:
            return {}
        path = self.base / bc.names_file
        try:
            mtime = path.stat().st_mtime
            if self._items_cache is not None and self._items_cache[0] == mtime:
                return self._items_cache[1]
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            names = {(int(k, 0) if isinstance(k, str) else int(k)): str(v)
                     for k, v in (raw.get("items") or {}).items()}
            self._items_cache = (mtime, names)
            return names
        except Exception:  # noqa: BLE001 — names are cosmetic, never fatal
            return self._items_cache[1] if self._items_cache else {}

    def _bearings(self, ram: dict) -> str | None:
        """Render live bearings to waypoints on the current map, from the run
        dir's HOT waypoints.yaml. Missing/empty/broken file -> None."""
        path = self.runlog.dir / "waypoints.yaml"
        try:
            mtime = path.stat().st_mtime
            if self._wp_cache is None or self._wp_cache[0] != mtime:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                self._wp_cache = (mtime, raw.get("waypoints") or {})
            parts = []
            for name, wp in self._wp_cache[1].items():
                if wp.get("map") != ram["map_id"]:
                    continue
                dx, dy = wp["x"] - ram["pos_x"], wp["y"] - ram["pos_y"]
                if not dx and not dy:
                    parts.append(f"{name}: you are here")
                    continue
                d = []
                if dy:
                    d.append(f"{abs(dy)} {'south' if dy > 0 else 'north'}")
                if dx:
                    d.append(f"{abs(dx)} {'east' if dx > 0 else 'west'}")
                parts.append(f"{name}: " + ", ".join(d))
            return "; ".join(parts) or None
        except Exception:  # noqa: BLE001 — bearings are optional context
            return None

    _GEN1_STATUS = ((0x08, "POISONED"), (0x10, "BURNED"), (0x20, "FROZEN"),
                    (0x40, "PARALYZED"))

    @staticmethod
    def _gen1_text(bs: bytes) -> str:
        out = []
        for b in bs:
            if b == 0x50:
                break
            if 0x80 <= b <= 0x99:
                out.append(chr(ord("A") + b - 0x80))
            elif 0xA0 <= b <= 0xB9:
                out.append(chr(ord("a") + b - 0xA0))
            elif 0xF6 <= b <= 0xFF:
                out.append(str(b - 0xF6))
            else:
                out.append("?")
        return "".join(out)

    def _move_names(self) -> dict[int, str]:
        """HOT move-name table (data/<game>/moves.yaml), cached on mtime."""
        pc = self.profile.party
        if pc is None or not pc.moves_file:
            return {}
        path = self.base / pc.moves_file
        try:
            mtime = path.stat().st_mtime
            if self._moves_cache is not None and self._moves_cache[0] == mtime:
                return self._moves_cache[1]
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            names = {(int(k, 0) if isinstance(k, str) else int(k)): str(v)
                     for k, v in (raw.get("moves") or {}).items()}
            self._moves_cache = (mtime, names)
            return names
        except Exception:  # noqa: BLE001 — names are cosmetic, never fatal
            return self._moves_cache[1] if self._moves_cache else {}

    def _species(self) -> dict[int, tuple[str, list[str]]]:
        """HOT species table: internal id -> (name, [types])."""
        pc = self.profile.party
        if pc is None or not pc.names_file:
            return {}
        try:
            raw = yaml.safe_load(
                (self.base / pc.names_file).read_text(encoding="utf-8"))
            out = {}
            for k, v in ((raw or {}).get("species") or {}).items():
                sid = int(k, 0) if isinstance(k, str) else int(k)
                if isinstance(v, dict):
                    out[sid] = (str(v.get("name", f"SPECIES_0x{sid:02x}")),
                                [str(t) for t in v.get("types", [])])
                else:
                    out[sid] = (str(v), [])
            return out
        except Exception:  # noqa: BLE001 — cosmetic
            return {}

    def _type_data(self) -> tuple[dict[int, str], dict[str, dict[str, float]]]:
        """HOT type table: RAM type-id byte -> name, and the attack chart."""
        bt = self.profile.battle
        if bt is None or not bt.types_file:
            return {}, {}
        try:
            raw = yaml.safe_load(
                (self.base / bt.types_file).read_text(encoding="utf-8")) or {}
            ids = {int(k, 0): str(v)
                   for k, v in (raw.get("type_ids") or {}).items()}
            chart = {str(a): {str(d): float(m) for d, m in (row or {}).items()}
                     for a, row in (raw.get("chart") or {}).items()}
            return ids, chart
        except Exception:  # noqa: BLE001
            return {}, {}

    @staticmethod
    def _effect(attack_types: list[str], defend_types: list[str],
                chart: dict[str, dict[str, float]]) -> tuple[str, float]:
        """Best multiplier any of our types achieves vs the defender."""
        best_t, best_m = "", -1.0
        for at in attack_types:
            m = 1.0
            for dt in defend_types:
                m *= chart.get(at, {}).get(dt, 1.0)
            if m > best_m:
                best_t, best_m = at, m
        return best_t, best_m

    @staticmethod
    def _mult_word(m: float) -> str:
        if m == 0:
            return "NO effect"
        if m >= 2:
            return f"{m:g}x (super effective!)"
        if m < 1:
            return f"{m:g}x (resisted)"
        return "1x"

    def _read_party(self) -> str:
        """Render party state: 'A (CHARMANDER) lv8 HP 16/24' per mon, plus
        status words and a LOW! tag under quarter HP."""
        pc = self.profile.party
        n = min(self.extras.read_block(pc.count_addr, 1)[0], 6)
        if not n:
            return ""
        species = self._species()
        out = []
        for i in range(n):
            mon = self.extras.read_block(pc.mons_addr + i * pc.mon_size,
                                         pc.mon_size)
            nick = self._gen1_text(
                self.extras.read_block(pc.nicks_addr + i * pc.nick_size,
                                       pc.nick_size))
            sp = species.get(mon[0], (f"SPECIES_0x{mon[0]:02x}", []))[0]
            hp = (mon[pc.hp_off] << 8) | mon[pc.hp_off + 1]
            mx = (mon[pc.maxhp_off] << 8) | mon[pc.maxhp_off + 1]
            s = f"{nick} ({sp}) lv{mon[pc.level_off]} HP {hp}/{mx}"
            for bit, word in self._GEN1_STATUS:
                if mon[pc.status_off] & bit:
                    s += f" {word}"
            if mon[pc.status_off] & 0x07:
                s += " ASLEEP"
            # move slots IN MENU ORDER with live PP — battle move selection
            # (slot number = DOWN presses) and PP exhaustion must be
            # visible, not remembered
            mnames = self._move_names()
            slots = []
            for j in range(4):
                mid = mon[pc.moves_off + j]
                if not mid:
                    continue
                pp = mon[pc.pp_off + j] & 0x3F  # top bits = PP-Up count
                nm = mnames.get(mid, f"MOVE_0x{mid:02x}")
                slots.append(f"{j + 1} {nm} ({pp} PP"
                             + (" - UNUSABLE!)" if pp == 0 else ")"))
            if slots:
                s += " - moves: " + ", ".join(slots)
            if mx and hp * 4 <= mx:
                s += " (LOW!)"
            out.append(s)
        return "; ".join(out)

    def _battle_hint(self) -> str:
        """Computed Gen 1 type math for the current battle: who the enemy
        is, how hard our types hit it, how hard its types hit us."""
        bt, pc = self.profile.battle, self.profile.party
        ids, chart = self._type_data()
        if not ids or not chart or pc is None:
            return ""
        e = self.extras.read_block(bt.enemy_addr, bt.maxhp_off + 2)
        et1, et2 = ids.get(e[bt.type1_off]), ids.get(e[bt.type2_off])
        if et1 is None:  # garbage struct (menu screens etc.) — stay silent
            return ""
        etypes = [t for t in dict.fromkeys((et1, et2)) if t]
        mon = self.extras.read_block(pc.mons_addr, 7)
        mt1, mt2 = ids.get(mon[5]), ids.get(mon[6])
        mtypes = [t for t in dict.fromkeys((mt1, mt2)) if t]
        species = self._species()
        name = species.get(e[0], (f"SPECIES_0x{e[0]:02x}", []))[0]
        hp = (e[bt.hp_off] << 8) | e[bt.hp_off + 1]
        mx = (e[bt.maxhp_off] << 8) | e[bt.maxhp_off + 1]
        parts = [f"enemy {name} lv{e[bt.level_off]} "
                 f"({'/'.join(etypes)}) HP {hp}/{mx}"]
        if mtypes:
            at, m = self._effect(mtypes, etypes, chart)
            parts.append(f"your {at} moves hit it {self._mult_word(m)}")
            dt, dm = self._effect(etypes, mtypes, chart)
            parts.append(f"its {dt} moves hit you {self._mult_word(dm)}")
        return "; ".join(parts)

    def _map_names(self) -> dict[int, str]:
        """HOT map-id -> place-name table (data/<game>/maps.yaml)."""
        path = self.base / "data" / self.profile.name / "maps.yaml"
        try:
            mtime = path.stat().st_mtime
            if self._maps_cache is not None and self._maps_cache[0] == mtime:
                return self._maps_cache[1]
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            names = {int(k): str(v) for k, v in (raw.get("maps") or {}).items()}
            self._maps_cache = (mtime, names)
            return names
        except Exception:  # noqa: BLE001 — names are context, never fatal
            return self._maps_cache[1] if self._maps_cache else {}

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
            ledges: set[int] = set()
            counters: set[int] = set()
            grass: set[int] = set()
            if self._terrain is not None or tm.walkable_by_tileset:
                # walkability is per-tileset: pick the set for the CURRENT
                # tileset; an unconfigured one degrades to the raw-id dump
                tileset = self.extras.read_block(tm.tileset_addr, 1)[0]
                walk: set[int] = set()
                if self._terrain is not None:
                    walk, portals, ledges, counters, grass = \
                        self._terrain.lookup(tileset)
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
            # last-seen grass per map: whenever grass is on screen, remember
            # the nearest patch's MAP coords — walk_to_grass heads toward it
            # later when the model stands somewhere with none visible
            map_id = self._last_ram.get("map_id")
            if player is not None and grass and map_id is not None:
                best = None
                for br in range(tm.rows // 2):
                    for bc in range(tm.cols // 2):
                        if raw[(br * 2 + 1) * tm.cols + bc * 2] in grass:
                            d = (abs(bc - tm.player_col // 2)
                                 + abs(br - tm.player_row // 2))
                            if best is None or d < best[0]:
                                best = (d, bc, br)
                if best is not None:
                    self._grass_seen[map_id] = _map_coord(
                        best[1] * 2, best[2] * 2, tm, px, py)
            hint = (self._grass_seen.get(map_id)
                    if player is not None and map_id is not None else None)
            self._nav = {"tiles": raw, "cfg": tm, "walkable": set(tm.walkable),
                         "npcs": npcs, "map_wh": map_wh, "player": player,
                         "warps": warps, "ledges": ledges, "counters": counters,
                         "grasses": grass,
                         "grass_hint": hint} if tm.walkable else None
            return render_ascii(raw, tm, player=player, map_wh=map_wh, warps=warps,
                                tileset=tileset, portal_ids=portals, npcs=npcs,
                                ledge_ids=ledges, grass_ids=grass)
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
