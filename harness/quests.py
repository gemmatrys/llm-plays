"""Structured quest feed — the checkpoint's plan in a harness-ingestible shape.

The quest tree moved INTO the harness 2026-07-22 (user decision, revising
the earlier checkpoint-side-only rule): the CHECKPOINT still authors every
word of it — act titles, quest texts, DONE lines, budgets, rules — but the
mechanical duties move from manual goals.md minting to this module:

- feed PIECEMEAL: the model sees the act ladder (done acts collapsed, YOU
  ARE HERE marked, future acts one line each), the done-quests-so-far of
  the current act, and exactly ONE current quest; later quests are withheld.
- run the TIME BUDGET: each quest carries `budget_min`; the loop escalates
  goal_overtime once when exceeded.
- record the model's marks: done_goal stamps a quest `done` (goal_stamped
  escalation — the checkpoint validates async, believe-and-stamp); a COACH
  note flips the current quest to `coach` so the flag is visible in the
  file the checkpoint opens.

The harness never judges a stamp, never reorders quests, never writes
content — glue only (PLAN §1).

File: runs/<game>/<run-id>/quests.yaml, seeded from prompts/<game>/
quests.yaml at run creation. HOT both ways: the checkpoint edits it live
(rewrites, un-stamps, act refreshes) and this module writes status marks;
reload is mtime-driven, a parse error keeps the last good tree (the
caller escalates quests_invalid). The live copy is machine-rewritten on
every mark — checkpoint commentary belongs in the seed or the master
plan, not in live-file comments.

Schema (yaml):
    game_goal: one line, the root of the ladder
    preamble: |            rendered under the ladder (the COACH contract)
    rules: |               global rules, always rendered
    acts:
      - id: act0
        title: player-voice line, rendered verbatim in the ladder
        verify: checkpoint-only stamp-validation anchor; echoed into
                act_stamped escalations, never rendered to the model
        rules_extra: |     optional, rendered only while this act is current
        quests:
          - id: a0-newgame
            title: short label (collapsed done-list rendering)
            status: todo | done | coach
            budget_min: 15
            text: |        the quest body, model voice
            done: the DONE condition, state-line vocabulary
Display numbers are positional (1-based across the whole file) — stable
enough for the one-current-quest contract; identity for edits is `id`.
"""
from __future__ import annotations

from pathlib import Path

import yaml


class _LiteralStr(str):
    pass


def _literal_presenter(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data,
                                   style="|" if "\n" in data else None)


class _Dumper(yaml.SafeDumper):
    pass


_Dumper.add_representer(str, _literal_presenter)
_Dumper.add_representer(_LiteralStr, _literal_presenter)


class QuestBook:
    """Load/render/mark the run's quests.yaml. All read methods reload on
    mtime change; a parse error keeps the last good tree and surfaces in
    `self.error` for the caller to escalate."""

    def __init__(self, path: Path):
        self.path = path
        self._mtime: float | None = None
        self._data: dict | None = None
        self.error: str | None = None
        self._refresh()

    @property
    def active(self) -> bool:
        return self._data is not None

    # ---------- loading ----------

    def _refresh(self) -> None:
        try:
            if not self.path.is_file():
                return
            mtime = self.path.stat().st_mtime
            if self._mtime == mtime and self._data is not None:
                return
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or not raw.get("acts"):
                raise ValueError("quests.yaml: no acts")
            for act in raw["acts"]:
                if "title" not in act:
                    raise ValueError("an act is missing its title")
                for q in act.get("quests") or []:
                    if "text" not in q:
                        raise ValueError(
                            f"a quest in act '{act.get('id')}' has no text")
            self._data = raw
            self._mtime = mtime
            self.error = None
        except Exception as e:  # noqa: BLE001 — bad edit degrades, never stalls
            self.error = repr(e)[:300]

    def _save(self) -> None:
        text = yaml.dump(self._data, Dumper=_Dumper, sort_keys=False,
                         allow_unicode=True, width=72)
        self.path.write_text(text, encoding="utf-8")
        self._mtime = self.path.stat().st_mtime

    # ---------- structure ----------

    def _numbered(self) -> list[tuple[int, dict, dict]]:
        """[(display_n, act, quest)] in file order."""
        out, n = [], 0
        for act in (self._data or {}).get("acts", []):
            for q in act.get("quests") or []:
                n += 1
                out.append((n, act, q))
        return out

    def current(self) -> tuple[int, dict, dict] | None:
        """First quest not marked done (coach-flagged quests stay current —
        the flag asks for help, it does not skip the work)."""
        self._refresh()
        for n, act, q in self._numbered():
            if q.get("status") != "done":
                return n, act, q
        return None

    def all_done(self) -> bool:
        self._refresh()
        return self.active and self.current() is None

    def act_of_current(self) -> dict | None:
        cur = self.current()
        return cur[1] if cur else None

    # ---------- model marks ----------

    def mark_done(self, n: int) -> tuple[bool, dict | None]:
        """Stamp quest `n` done. Returns (marked, act_just_finished): the
        act dict when this stamp completed an act's last open quest — the
        caller escalates act_stamped with the act's verify anchor."""
        self._refresh()
        if not self.active:
            return False, None
        for num, act, q in self._numbered():
            if num == n and q.get("status") != "done":
                q["status"] = "done"
                self._save()
                finished = all(qq.get("status") == "done"
                               for qq in act.get("quests") or [])
                return True, act if finished else None
        return False, None

    def mark_coach(self, n: int) -> bool:
        """Flag quest `n` as needing coaching (visible in the file; the
        quest stays current). No-op on done quests."""
        self._refresh()
        if not self.active:
            return False
        for num, _act, q in self._numbered():
            if num == n and q.get("status") not in ("done", "coach"):
                q["status"] = "coach"
                self._save()
                return True
        return False

    # ---------- rendering (the model's whole view of strategy) ----------

    def render(self) -> str:
        """The derivation contract, implemented: act ladder with done acts
        collapsed and YOU ARE HERE, done-quest collapse for the current
        act, ONE current quest with its DONE line and time budget, global
        rules + the current act's extras. Checkpoint-only fields (verify,
        ids) are never rendered."""
        self._refresh()
        if not self.active:
            return ""
        data = self._data
        cur = self.current()
        cur_act = cur[1] if cur else None
        lines = ["THE ROAD TO THE END (why your current quest matters):"]
        goal = data.get("game_goal")
        if goal:
            lines.append(f"- {goal}")
        done_titles = []
        for act in data.get("acts", []):
            quests = act.get("quests") or []
            act_done = quests and all(q.get("status") == "done"
                                      for q in quests)
            if act_done:
                done_titles.append(act["title"])
                continue
            if done_titles:
                lines.append("  Done: " + "; ".join(done_titles) + ".")
                done_titles = []
            marker = "  <- YOU ARE HERE" if act is cur_act else ""
            lines.append(f"  - {act['title']}{marker}")
        if done_titles:  # everything done
            lines.append("  Done: " + "; ".join(done_titles) + ".")
        out = "\n".join(lines) + "\n"
        if data.get("preamble"):
            out += data["preamble"].rstrip() + "\n"
        out += "\n"
        if cur is not None:
            n, act, q = cur
            done_here = [qq.get("title") or "(unnamed)"
                         for qq in act.get("quests") or []
                         if qq.get("status") == "done"]
            if done_here:
                out += "Done so far: " + "; ".join(done_here) + ".\n\n"
            out += ("Your CURRENT quest - the only one; the next arrives "
                    "when this one is truly done:\n\n")
            body = q["text"].rstrip().splitlines()
            out += f"{n}. " + (body[0] if body else "") + "\n"
            out += "".join("   " + ln + "\n" for ln in body[1:])
            if q.get("done"):
                out += (f"   DONE when {q['done'].rstrip()}: mark quest "
                        f"{n} done then.\n")
            if q.get("budget_min"):
                out += f"   Time budget: {int(q['budget_min'])} minutes.\n"
            out += "\n"
        else:
            out += ("Every written quest is done - hold position; new "
                    "instructions are on the way.\n\n")
        rules = (data.get("rules") or "").rstrip()
        extra = ((cur_act or {}).get("rules_extra") or "").rstrip()
        if rules or extra:
            out += rules + ("\n" + extra if extra else "") + "\n"
        return out
