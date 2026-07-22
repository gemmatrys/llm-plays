"""Run directory: structured logs, metrics, snapshots, escalations, goals.

Layout (PLAN §4):
    runs/<game>/<run-id>/{goals.md, progress.md, log.jsonl, metrics.jsonl,
                          escalations.jsonl, snapshots/}
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
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
                 initial_goals: str | None = None,
                 initial_quests: str | None = None,
                 alert_cmd: list[str] | None = None,
                 alert_cooldown_s: float = 300.0):
        self.alert_cmd = alert_cmd
        self.alert_cooldown_s = alert_cooldown_s
        self._last_alert_ts = 0.0
        run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        self.dir = base / "runs" / game / run_id
        self.snapshots = self.dir / "snapshots"
        self.snapshots.mkdir(parents=True, exist_ok=True)
        self.goals_path = self.dir / "goals.md"
        # run-id reuse (restart/recovery): keep the run's goals — checkpoints
        # may have rewritten them and a restart must not clobber that
        self.resumed = self.goals_path.exists()
        if not self.resumed:
            self.goals_path.write_text(initial_goals or DEFAULT_GOALS,
                                       encoding="utf-8")
        # structured quest feed: seeded once from prompts/<game>/quests.yaml;
        # never clobbered on restart (the live copy carries model stamps and
        # checkpoint edits). When present it supersedes goals.md (loop.py).
        self.quests_path = self.dir / "quests.yaml"
        if initial_quests and not self.quests_path.exists():
            self.quests_path.write_text(initial_quests, encoding="utf-8")
        # the model's own notes ("I am upstairs in the Viridian Pokemon Center,
        # here to heal"). Written by the model, carried verbatim, survives
        # restarts; checkpoints may correct false beliefs in it.
        self.memory_path = self.dir / "memory.md"
        # run-scoped lessons a checkpoint records for THIS run (published to
        # the live branch under the run id); global truths go to LEARNINGS.md
        self.learnings_path = self.dir / "learnings.md"
        self._log = (self.dir / "log.jsonl").open("a", encoding="utf-8")
        self._metrics = (self.dir / "metrics.jsonl").open("a", encoding="utf-8")
        self._escalations = self.dir / "escalations.jsonl"
        # the loop and the live-publisher thread both log; keep lines whole
        self._write_lock = threading.Lock()

    def goals(self) -> str:
        return self.goals_path.read_text(encoding="utf-8")

    def quests(self) -> str:
        if self.quests_path.is_file():
            return self.quests_path.read_text(encoding="utf-8")
        return ""

    def memory(self) -> str:
        if self.memory_path.is_file():
            return self.memory_path.read_text(encoding="utf-8")
        return ""

    def set_memory(self, text: str) -> None:
        self.memory_path.write_text(text, encoding="utf-8")

    def learnings(self) -> str:
        if self.learnings_path.is_file():
            return self.learnings_path.read_text(encoding="utf-8")
        return ""

    def goals_finished(self) -> bool:
        """True when the HIGHEST-numbered goal in goals.md carries [DONE].
        Not all-stamped: instruction-style middle goals ("stop talking to
        the old man") never earn a stamp, so the last goal is the reliable
        end-of-objectives signal — reaching it means the run needs its next
        stretch written."""
        last: str | None = None
        last_n = -1
        for line in self.goals().splitlines():
            s = line.lstrip()
            if s and s[0].isdigit() and "." in s[:4]:
                n = int(s.split(".", 1)[0])
                if n >= last_n:
                    last_n, last = n, line
        return last is not None and "[DONE]" in last

    def mark_goal_done(self, n: int) -> bool:
        """Stamp [DONE] on numbered goal `n` in goals.md (the model's only
        write access to its goals — via the done_goal schema field). Marking
        only, never deletion; checkpoints prune stamped goals at rewrite.
        Returns False (no-op) if goal `n` isn't found or is already stamped."""
        lines = self.goals().splitlines()
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith(f"{n}.") and "[DONE]" not in line:
                indent = line[:len(line) - len(stripped)]
                lines[i] = f"{indent}{n}. [DONE] " + \
                    stripped[len(f"{n}."):].lstrip()
                self.goals_path.write_text("\n".join(lines) + "\n",
                                           encoding="utf-8")
                return True
        return False

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
        if d.done_goal is not None:
            entry["done_goal"] = d.done_goal
        if d.thinking:
            entry["thinking"] = d.thinking  # chain-of-thought, for the record
        self._write(self._log, entry)

    def log_metric(self, kind: str, **data) -> None:
        self._write(self._metrics, {"ts": time.time(), "kind": kind, **data})

    def escalate(self, kind: str, detail: str, snapshot: str | None = None) -> None:
        with self._escalations.open("a", encoding="utf-8") as f:
            self._write(f, {"ts": time.time(), "kind": kind, "detail": detail,
                            "snapshot": snapshot, "resolved": False})
        self._alert(kind, detail, snapshot)

    def _alert(self, kind: str, detail: str, snapshot: str | None) -> None:
        """Escalations must ALERT, not just record: launch the configured
        command detached (a toast, webhook, or Claude wake). Cooldown-guarded
        so a repeating escalation (e.g. prompt_invalid every tick) can't spam;
        best-effort — an alert failure must never touch the loop."""
        if not self.alert_cmd:
            return
        now = time.time()
        if now - self._last_alert_ts < self.alert_cooldown_s:
            self.log_metric("alert_suppressed", escalation=kind)
            return
        self._last_alert_ts = now
        env = dict(os.environ, LLMPLAYS_KIND=kind, LLMPLAYS_DETAIL=detail,
                   LLMPLAYS_SNAPSHOT=snapshot or "", LLMPLAYS_RUN=str(self.dir))
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.Popen(self.alert_cmd, env=env, creationflags=flags,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log_metric("alert_fired", escalation=kind)
        except Exception as e:  # noqa: BLE001 — alerting is best-effort
            self.log_metric("alert_error", detail=repr(e)[-200:])

    def snapshot(self, frame: Frame, tag: str = "") -> str:
        name = f"{time.strftime('%Y%m%d-%H%M%S')}{('-' + tag) if tag else ''}.png"
        path = self.snapshots / name
        frame.image.save(path)
        return str(path)

    def _write(self, fh, obj: dict) -> None:
        with self._write_lock:
            if fh.closed:
                return  # async writers (live-publisher) may outlive the loop
            fh.write(json.dumps(obj, separators=(",", ":")) + "\n")
            fh.flush()

    def close(self) -> None:
        with self._write_lock:
            self._log.close()
            self._metrics.close()
