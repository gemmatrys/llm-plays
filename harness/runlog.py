"""Run directory: structured logs, metrics, snapshots, escalations, goals.

Layout (PLAN §4):
    runs/<game>/<run-id>/{goals.md, progress.md, log.jsonl, metrics.jsonl,
                          escalations.jsonl, snapshots/}
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .types import Decision, Frame

DEFAULT_GOALS = """# Goals

You are playing the game. Make progress: explore, talk to people, win battles,
advance the story. Avoid walking in circles. (This file is rewritten by Claude
checkpoints with specific objectives.)
"""


class RunLog:
    def __init__(self, base: Path, game: str, run_id: str | None = None,
                 initial_goals: str | None = None):
        run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        self.dir = base / "runs" / game / run_id
        self.snapshots = self.dir / "snapshots"
        self.snapshots.mkdir(parents=True, exist_ok=True)
        self.goals_path = self.dir / "goals.md"
        if not self.goals_path.exists():
            self.goals_path.write_text(initial_goals or DEFAULT_GOALS,
                                       encoding="utf-8")
        # the model's own notes ("I am upstairs in the Viridian Pokemon Center,
        # here to heal"). Written by the model, carried verbatim, survives
        # restarts; checkpoints may correct false beliefs in it.
        self.memory_path = self.dir / "memory.md"
        self._log = (self.dir / "log.jsonl").open("a", encoding="utf-8")
        self._metrics = (self.dir / "metrics.jsonl").open("a", encoding="utf-8")
        self._escalations = self.dir / "escalations.jsonl"

    def goals(self) -> str:
        return self.goals_path.read_text(encoding="utf-8")

    def memory(self) -> str:
        if self.memory_path.is_file():
            return self.memory_path.read_text(encoding="utf-8")
        return ""

    def set_memory(self, text: str) -> None:
        self.memory_path.write_text(text, encoding="utf-8")

    def log_decision(self, d: Decision, frame_hash: str, ram: dict | None,
                     duration_s: float, executed: int | None = None) -> None:
        names = [b.name for b in d.behaviors]
        entry = {
            "ts": time.time(), "behavior": names[0], "rung": int(d.rung),
            "reason": d.reason, "frame": frame_hash, "ram": ram,
            "duration_s": round(duration_s, 3),
        }
        if len(names) > 1:
            entry["plan"] = names
            entry["executed"] = executed
        if d.prompt_hash:
            entry["prompt"] = d.prompt_hash  # segment metrics by prompt version
        if d.memory_update is not None:
            entry["memory"] = d.memory_update  # notes rewrite, for replay/debug
        self._write(self._log, entry)

    def log_metric(self, kind: str, **data) -> None:
        self._write(self._metrics, {"ts": time.time(), "kind": kind, **data})

    def escalate(self, kind: str, detail: str, snapshot: str | None = None) -> None:
        with self._escalations.open("a", encoding="utf-8") as f:
            self._write(f, {"ts": time.time(), "kind": kind, "detail": detail,
                            "snapshot": snapshot, "resolved": False})

    def snapshot(self, frame: Frame, tag: str = "") -> str:
        name = f"{time.strftime('%Y%m%d-%H%M%S')}{('-' + tag) if tag else ''}.png"
        path = self.snapshots / name
        frame.image.save(path)
        return str(path)

    @staticmethod
    def _write(fh, obj: dict) -> None:
        fh.write(json.dumps(obj, separators=(",", ":")) + "\n")
        fh.flush()

    def close(self) -> None:
        self._log.close()
        self._metrics.close()
