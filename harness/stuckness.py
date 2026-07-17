"""Mechanical stuckness detection — invariant I3.

No LLM judgement involved: if the set of distinct screens seen recently is tiny for
too long, we are stuck, and an escalation fires (rate-limited to protect the Claude
budget).
"""
from __future__ import annotations

import time
from collections import deque

from .profile import EscalationConfig


class StucknessMonitor:
    def __init__(self, cfg: EscalationConfig, window_size: int = 200,
                 distinct_threshold: int = 3):
        self.cfg = cfg
        self._hashes: deque[str] = deque(maxlen=window_size)
        self._last_novel_ts = time.time()
        self._wake_times: deque[float] = deque()
        self.distinct_threshold = distinct_threshold

    def observe(self, frame_hash: str) -> None:
        if frame_hash not in self._hashes:
            self._last_novel_ts = time.time()
        self._hashes.append(frame_hash)

    def is_stuck(self) -> bool:
        stagnant = time.time() - self._last_novel_ts > self.cfg.stagnant_after_s
        few_screens = len(set(self._hashes)) <= self.distinct_threshold
        return stagnant and (few_screens or len(self._hashes) == self._hashes.maxlen)

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
        self._hashes.clear()
        self._last_novel_ts = time.time()
