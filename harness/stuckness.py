"""Mechanical stuckness detection — invariant I3.

No LLM judgement involved. Independent detectors, each purely mechanical, each
disabled by setting its threshold <= 0:

- screen:    no NOVEL phash (one absent from the recent membership window) for
             stagnant_after_s. The window makes cursor blinks, tile animation,
             and door-bounce oscillations count as stagnant — only a genuinely
             new screen resets the clock.
- position:  map_id + player tile pinned inside a pos_box_tiles box for
             pos_stagnant_after_s with no non-position RAM change. Covers the
             screen detector's blind spot, proven by the naming-grid wedge: a
             UI that echoes inputs back mints a novel phash per keypress and
             holds the screen clock at bay indefinitely.
- behaviors: the policy chose from <= behavior_distinct_max distinct behaviors
             for behavior_stagnant_after_s while the position was pinned and no
             milestone landed — the mechanical version of prompt.md's "watch
             your recent actions", which a model acting on a false belief will
             not apply to itself. The position gate keeps a legitimate long
             walk (10 min of press_UP is one behavior, zero milestones) from
             counting. Fires earlier than the position detector; tune the two
             windows together.
- milestone: no milestone (non-position RAM change: badge/map/party) for
             milestone_stagnant_after_s. The slowest, surest alarm — pure
             progress, no screen proxy. Armed only once RAM has been seen, so
             a RAM-less (console) run can't false-fire it.

The response is staged — loop.py drives it via next_response(): one bounded
random-input self-rescue first (the same get_unstuck escape hatch the model
can pick, so it costs nothing new), then a rate-limited Claude escalation if
signals persist past the rescue grace period. Milestone-only stuckness skips
the rescue — random buttons don't help "exploring but not progressing".
"""
from __future__ import annotations

import time
from collections import deque

from .profile import EscalationConfig


class StucknessMonitor:
    def __init__(self, cfg: EscalationConfig, window_size: int = 200):
        self.cfg = cfg
        now = time.time()
        self._hashes: deque[str] = deque(maxlen=window_size)
        self._last_novel_ts = now
        self._pos_anchor: tuple[int, int, int] | None = None  # (map, x, y)
        self._pos_anchor_ts = now
        self._milestone_ts = now  # last non-position RAM change (note_milestone)
        self._has_ram = False
        # (ts, names-executed-that-decision); sized so even a 2 s cadence keeps
        # more history than the behavior window needs
        self._behaviors: deque[tuple[float, frozenset[str]]] = deque(maxlen=1024)
        self._wake_times: deque[float] = deque()
        self._rescued_episode = False
        self._last_rescue_ts = 0.0

    def observe(self, frame_hash: str, ram: dict | None,
                behaviors: list[str]) -> None:
        now = time.time()
        if frame_hash not in self._hashes:
            self._last_novel_ts = now
        self._hashes.append(frame_hash)
        if ram is not None:
            self._has_ram = True
            if all(k in ram for k in ("map_id", "pos_x", "pos_y")):
                p = (ram["map_id"], ram["pos_x"], ram["pos_y"])
                a = self._pos_anchor
                if (a is None or p[0] != a[0]
                        or abs(p[1] - a[1]) > self.cfg.pos_box_tiles
                        or abs(p[2] - a[2]) > self.cfg.pos_box_tiles):
                    self._pos_anchor, self._pos_anchor_ts = p, now
        if behaviors:
            self._behaviors.append((now, frozenset(behaviors)))

    def note_milestone(self) -> None:
        """Loop calls this on any non-position RAM change. Real progress also
        closes the rescue episode: the next wedge earns a fresh self-rescue."""
        self._milestone_ts = time.time()
        self._rescued_episode = False

    def stuck_reasons(self) -> list[str]:
        """Every currently-firing detector, by name. Empty = not stuck."""
        now = time.time()
        c = self.cfg
        reasons = []
        if 0 < c.stagnant_after_s < now - self._last_novel_ts:
            reasons.append("screen")
        # how long the player has been pinned near the anchor; each detector
        # below compares this against its OWN window
        pinned_for = (now - self._pos_anchor_ts
                      if self._pos_anchor is not None else 0.0)
        if (c.pos_stagnant_after_s > 0 and pinned_for > c.pos_stagnant_after_s
                and now - self._milestone_ts > c.pos_stagnant_after_s):
            reasons.append("position")
        w = c.behavior_stagnant_after_s
        if (w > 0 and pinned_for > w and now - self._milestone_ts > w
                and self._behaviors and self._behaviors[0][0] <= now - w):
            distinct: set[str] = set()
            for ts, names in self._behaviors:
                if ts >= now - w:
                    distinct |= names
            if 0 < len(distinct) <= c.behavior_distinct_max:
                reasons.append("behaviors")
        if (c.milestone_stagnant_after_s > 0 and self._has_ram
                and now - self._milestone_ts > c.milestone_stagnant_after_s):
            reasons.append("milestone")
        return reasons

    def next_response(self, reasons: list[str], allow_random: bool) -> str:
        """Staged I3 response for a non-empty stuck signal: 'rescue' (inject one
        random-input escape burst), 'wait' (a rescue is still inside its grace
        period), or 'escalate'."""
        now = time.time()
        if self._rescued_episode and now - self._last_rescue_ts <= self.cfg.rescue_grace_s:
            return "wait"
        rescuable = (self.cfg.self_rescue and allow_random
                     and not self._rescued_episode)
        if rescuable and any(r != "milestone" for r in reasons):
            self._rescued_episode = True
            self._last_rescue_ts = now
            return "rescue"
        return "escalate"

    def may_wake_claude(self) -> bool:
        """Rate limiter: at most max_wakes_per_window escalation wakes per window."""
        now = time.time()
        while self._wake_times and now - self._wake_times[0] > self.cfg.window_s:
            self._wake_times.popleft()
        if len(self._wake_times) >= self.cfg.max_wakes_per_window:
            return False
        self._wake_times.append(now)
        return True

    def reset(self) -> None:
        """Called after an escalation: rearm every clock — including the
        milestone alarm, whose escalation IS the response to "no progress";
        leaving it firing would just spam the rate limiter every tick."""
        now = time.time()
        self._hashes.clear()
        self._last_novel_ts = now
        self._pos_anchor = None
        self._pos_anchor_ts = now
        self._behaviors.clear()
        self._milestone_ts = now
        self._rescued_episode = False
