"""Async live-publisher: a per-run `live/<run-id>` branch forked from main.

The first publish of a run creates branch `live/<run-id>` with the CURRENT
main commit as its parent — the branch is rooted in the exact code the run
executes. Every pass then commits the run's actual running state on top, at
real repo paths:

- the run's `goals.md` / `memory.md` / `learnings.md`
  (under `runs/<game>/<run-id>/`, gitignored on main, tracked here)
- the hot Gemma-facing surfaces exactly as they are on DISK, including
  uncommitted checkpoint edits: `prompts/<game>/*.md` and the skill
  libraries (`skills/*/*.yaml`)

So the branch is the complete record of what ran: the code base it forked
from, plus every mid-run goal/prompt/skill change as its own commit. Durable
fixes graduate to main separately (checkpoint duty 5) so the NEXT clean run
forks from an improved base; run-scoped state never lands on main.

Commits are built with git plumbing against a temporary GIT_INDEX_FILE
(hash-object -> read-tree -> update-index -> write-tree -> commit-tree ->
update-ref) and never touch the working tree, the real index, or the
checked-out branch — the publisher cannot collide with development work or
harness state in the same repository.

Rules:
- one commit per pass covering whichever files changed; only-on-change
- best-effort: git failures are logged as metrics and retried on later
  passes (unpushed commits re-push every pass, flushing the backlog once
  the network is back)
- the thread is a daemon: it can never keep the harness alive or wedge it
"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path


class LivePublisher:
    def __init__(self, base: Path, runlog, profile=None, poll_s: float = 1.0):
        self.base = Path(base)
        self.runlog = runlog
        self.run_id = runlog.dir.name
        self.branch = f"live/{self.run_id}"
        self.ref = f"refs/heads/{self.branch}"
        self.poll_s = poll_s
        self._index_path = runlog.dir / ".publish.index"  # runs/ is gitignored
        rel = runlog.dir.relative_to(self.base).as_posix()

        def _read_wp() -> str:
            p = runlog.dir / "waypoints.yaml"
            try:
                return p.read_text(encoding="utf-8") if p.is_file() else ""
            except OSError:
                return ""  # mid-write; next pass catches up

        self._run_sources = {f"{rel}/goals.md": runlog.goals,
                             f"{rel}/memory.md": runlog.memory,
                             f"{rel}/learnings.md": runlog.learnings,
                             f"{rel}/waypoints.yaml": _read_wp}
        # hot surfaces watched straight from disk (uncommitted edits included)
        self._watch: list[tuple[str, str]] = []
        if profile is not None:
            self._watch.append((f"prompts/{profile.name}", "*.md"))
            self._watch.append((f"data/{profile.name}", "*.yaml"))
            self._watch += [(d, "*.yaml") for d in profile.skills_dirs]
        self._published: dict[str, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- lifecycle ------------------------------------------------------------
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="live-publisher")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)

    def _run(self) -> None:
        while not self._stop.wait(self.poll_s):
            try:
                self.step()
            except Exception as e:  # noqa: BLE001 — the watcher must survive
                self.runlog.log_metric("publish_error", detail=repr(e)[-300:])

    # -- one pass -------------------------------------------------------------
    def _gather(self) -> dict[str, str]:
        targets = {path: read() for path, read in self._run_sources.items()}
        for d, pattern in self._watch:
            dp = self.base / d
            if not dp.is_dir():
                continue
            for f in sorted(dp.glob(pattern)):
                try:
                    targets[f.relative_to(self.base).as_posix()] = \
                        f.read_text(encoding="utf-8")
                except OSError:
                    pass  # mid-write or vanished; the next pass catches up
        return targets

    def step(self) -> None:
        targets = self._gather()
        # empty AND never published isn't a change (learnings.md before the
        # first checkpoint); empty after being published = a deletion
        changed = [p for p, c in targets.items()
                   if c != self._published.get(p)
                   and (c or self._published.get(p))]
        removed = [p for p, c in self._published.items()
                   if c and p not in targets]
        if not changed and not removed:
            return  # push failures retry via changed-detection: a failed pass
                    # never marks content published, so it re-runs entirely
        if self._build_and_push(targets, changed, removed):
            self._published = dict(targets)
            names = [Path(p).name for p in changed] + \
                    [f"-{Path(p).name}" for p in removed]
            self.runlog.log_metric("publish", files=names, branch=self.branch)

    # -- git plumbing ---------------------------------------------------------
    def _git(self, *args: str, input_text: str | None = None,
             index: bool = False) -> subprocess.CompletedProcess:
        # binary I/O on purpose: text mode on Windows rewrites \n as \r\n on
        # stdin, which corrupts blob contents
        env = dict(os.environ, GIT_INDEX_FILE=str(self._index_path)) \
            if index else None
        r = subprocess.run(["git", "-C", str(self.base), *args],
                           capture_output=True, timeout=60, env=env,
                           input=input_text.encode("utf-8")
                           if input_text is not None else None)
        r.stdout = r.stdout.decode("utf-8", errors="replace")
        r.stderr = r.stderr.decode("utf-8", errors="replace")
        return r

    def _fail(self, stage: str, r: subprocess.CompletedProcess) -> bool:
        self.runlog.log_metric("publish_error", stage=stage,
                               detail=(r.stderr or r.stdout)[-300:])
        return False

    def _fork_parent(self) -> str | None:
        """Branch head if it exists, else current main/master (the fork)."""
        r = self._git("rev-parse", "--verify", "--quiet", self.ref)
        if r.returncode == 0:
            return r.stdout.strip()
        for cand in ("main", "master"):
            r = self._git("rev-parse", "--verify", "--quiet", cand)
            if r.returncode == 0:
                return r.stdout.strip()
        return None

    def _build_and_push(self, targets: dict[str, str], changed: list[str],
                        removed: list[str]) -> bool:
        parent = self._fork_parent()
        if parent is None:
            self.runlog.log_metric("publish_error", stage="fork-base",
                                   detail="no live/<id>, main, or master ref")
            return False

        r = self._git("read-tree", parent, index=True)
        if r.returncode != 0:
            return self._fail("read-tree", r)
        for path in changed:
            content = targets[path]
            if not content:  # published before, empty now -> treat as removed
                removed = removed + [path]
                continue
            r = self._git("hash-object", "-w", "--stdin", input_text=content)
            if r.returncode != 0:
                return self._fail("hash-object", r)
            r = self._git("update-index", "--add", "--cacheinfo",
                          f"100644,{r.stdout.strip()},{path}", index=True)
            if r.returncode != 0:
                return self._fail("update-index", r)
        for path in removed:
            r = self._git("update-index", "--force-remove", "--", path,
                          index=True)
            if r.returncode != 0:
                return self._fail("update-index-rm", r)
        r = self._git("write-tree", index=True)
        if r.returncode != 0:
            return self._fail("write-tree", r)
        tree = r.stdout.strip()

        names = [Path(p).name for p in changed] + \
                [f"-{Path(p).name}" for p in removed]
        r = self._git("commit-tree", tree, "-m",
                      f"live: {self.run_id}: " + ", ".join(names),
                      "-p", parent)
        if r.returncode != 0:
            return self._fail("commit-tree", r)
        commit = r.stdout.strip()

        r = self._git("update-ref", self.ref, commit)
        if r.returncode != 0:
            return self._fail("update-ref", r)

        r = self._git("push", "origin", f"{self.ref}:{self.ref}")
        if r.returncode != 0:
            return self._fail("push", r)
        return True
