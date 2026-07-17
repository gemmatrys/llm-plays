"""Hot sync for skills: pick up checkpoint-authored behaviors mid-run.

The prompt needs no watcher — prompts/<game>/prompt.md is read fresh on every
LLM invocation, so edits are live on the next decision by construction.

Skills do need one: a new or edited YAML must be loaded into the behavior
library before the executor can run it. This watcher polls mtimes (a handful
of stat() calls, once per tick) and reloads the library in place on change.
The new skills then appear to the LLM automatically: the {behaviors}
placeholder and the plan JSON schema are both built from the live library on
each request — that is the "link" the model reads.
"""
from __future__ import annotations

from pathlib import Path

from .behaviors import BehaviorLibrary


class HotSync:
    def __init__(self, base: Path, skills_dirs: list[str], library: BehaviorLibrary):
        self.base = Path(base)
        self.skills_dirs = skills_dirs
        self.library = library
        self._snapshot = self._scan()

    def _scan(self) -> dict[str, int]:
        state: dict[str, int] = {}
        for d in self.skills_dirs:
            dd = self.base / d
            if dd.is_dir():
                for f in sorted(dd.glob("*.yaml")):
                    state[str(f)] = f.stat().st_mtime_ns
        return state

    def poll(self) -> list[str]:
        """Reload the library if skill files changed; return changed file names."""
        new = self._scan()
        if new == self._snapshot:
            return []
        changed = [p for p, m in new.items() if self._snapshot.get(p) != m]
        changed += [p for p in self._snapshot if p not in new]  # deletions
        self._snapshot = new
        self.library.reload_skills(self.skills_dirs, self.base)
        return [Path(p).name for p in changed]
