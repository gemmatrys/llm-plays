"""Async live-publisher: mirrors a run's goals/memory/learnings to a `live` branch.

A watcher thread — deliberately separate from the decision loop, so git
latency can never delay a decision — polls the run's goals.md, memory.md, and
learnings.md. Every change becomes a commit on the `live` branch, filed under
`<run-id>/` (previous runs' directories stay in the tree untouched): the
branch is the progression record across runs — each run's directory shows its
final state, the commit history shows every goal/notes change within it —
while `main` stays purely code.

Commits are built with git plumbing (hash-object -> mktree -> commit-tree ->
update-ref) and never touch the working tree, the index, or the checked-out
branch — the publisher cannot collide with development work or harness state
in the same repository.

Rules:
- one commit per pass covering whichever files changed; only-on-change
- best-effort: git failures are logged as metrics and retried on later
  passes (unpushed live commits are re-pushed every pass, which flushes the
  backlog once the network is back)
- the thread is a daemon: it can never keep the harness alive or wedge it
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path

BRANCH = "live"
REF = f"refs/heads/{BRANCH}"


class LivePublisher:
    def __init__(self, base: Path, runlog, poll_s: float = 1.0):
        self.base = Path(base)
        self.runlog = runlog
        self.run_id = runlog.dir.name
        self.poll_s = poll_s
        self._sources = {"goals.md": runlog.goals, "memory.md": runlog.memory,
                         "learnings.md": runlog.learnings}
        self._published: dict[str, str | None] = {n: None for n in self._sources}
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
    def step(self) -> None:
        targets = {name: read() for name, read in self._sources.items()}
        # a file that is empty AND was never published isn't a change — keeps
        # "learnings.md" out of commit messages before the first checkpoint
        changed = [n for n, content in targets.items()
                   if content != self._published[n]
                   and (content or self._published[n])]
        if not changed:
            return  # push failures retry via changed-detection: a failed pass
                    # never marks content as published, so it re-runs entirely
        if self._build_and_push(targets, changed):
            self._published = dict(targets)
            self.runlog.log_metric("publish", files=changed, branch=BRANCH,
                                   run=self.run_id)

    # -- git plumbing ---------------------------------------------------------
    def _git(self, *args: str, input_text: str | None = None
             ) -> subprocess.CompletedProcess:
        # binary I/O on purpose: text mode on Windows rewrites \n as \r\n on
        # stdin, which corrupts blob contents and puts \r into mktree filenames
        r = subprocess.run(["git", "-C", str(self.base), *args],
                           capture_output=True, timeout=60,
                           input=input_text.encode("utf-8")
                           if input_text is not None else None)
        r.stdout = r.stdout.decode("utf-8", errors="replace")
        r.stderr = r.stderr.decode("utf-8", errors="replace")
        return r

    def _fail(self, stage: str, r: subprocess.CompletedProcess) -> bool:
        self.runlog.log_metric("publish_error", stage=stage,
                               detail=(r.stderr or r.stdout)[-300:])
        return False

    def _build_and_push(self, targets: dict[str, str], changed: list[str]) -> bool:
        blobs = {}
        for name, content in targets.items():
            if not content:
                continue  # absent files (learnings before the first checkpoint)
            r = self._git("hash-object", "-w", "--stdin", input_text=content)
            if r.returncode != 0:
                return self._fail("hash-object", r)
            blobs[name] = r.stdout.strip()

        sub_listing = "".join(f"100644 blob {sha}\t{name}\n"
                              for name, sha in sorted(blobs.items()))
        r = self._git("mktree", input_text=sub_listing)
        if r.returncode != 0:
            return self._fail("mktree", r)
        subtree = r.stdout.strip()

        # root tree = current live tree with THIS run's directory swapped in;
        # other runs' directories ride along untouched, so the branch
        # accumulates a per-run progression record instead of overwriting
        parent = self._git("rev-parse", "--verify", "--quiet", REF)
        entries: list[str] = []
        if parent.returncode == 0:
            r = self._git("ls-tree", REF)
            if r.returncode != 0:
                return self._fail("ls-tree", r)
            entries = [ln for ln in r.stdout.splitlines()
                       if ln and not ln.endswith(f"\t{self.run_id}")]
        entries.append(f"040000 tree {subtree}\t{self.run_id}")
        r = self._git("mktree", input_text="\n".join(entries) + "\n")
        if r.returncode != 0:
            return self._fail("mktree-root", r)
        tree = r.stdout.strip()

        commit_args = ["commit-tree", tree, "-m",
                       f"live: {self.run_id}: " + ", ".join(changed)]
        if parent.returncode == 0:
            commit_args += ["-p", parent.stdout.strip()]
        r = self._git(*commit_args)
        if r.returncode != 0:
            return self._fail("commit-tree", r)
        commit = r.stdout.strip()

        r = self._git("update-ref", REF, commit)
        if r.returncode != 0:
            return self._fail("update-ref", r)

        r = self._git("push", "origin", f"{REF}:{REF}")
        if r.returncode != 0:
            return self._fail("push", r)
        return True
