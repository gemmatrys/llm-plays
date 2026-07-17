"""Checkpoint briefing: the context bundle the harness hands to Claude.

Deterministic aggregation of a run directory into briefing.md — counts, rates,
milestones, open escalations, current goals/memory, prompt-version table. No
interpretation: diagnosis is the checkpoint's job; this saves it from spending
its budget parsing JSONL.

Generated automatically when an escalation fires (so an early-wake finds a
fresh briefing) and manually / from the scheduled checkpoint via:

    python -m harness.briefing runs/<game>/<run-id>
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

RUNG_NAMES = {1: "LLM", 2: "SCRIPTED", 3: "SAFE_IDLE", 4: "RANDOM(fish)"}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # torn line (harness was writing); skip
    return out


def _ago(ts: float, now: float) -> str:
    m = max(0, int((now - ts) / 60))
    return f"{m // 60}h{m % 60:02d}m ago"


def build_briefing(run_dir: Path, now: float | None = None) -> str:
    now = now or time.time()
    log = _read_jsonl(run_dir / "log.jsonl")
    metrics = _read_jsonl(run_dir / "metrics.jsonl")
    escalations = _read_jsonl(run_dir / "escalations.jsonl")

    lines = [f"# Checkpoint briefing — {run_dir.name}",
             f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}",
             f"Run dir: {run_dir}", ""]

    # -- totals ---------------------------------------------------------------
    lines.append("## Run totals")
    if log:
        hours = max((log[-1]["ts"] - log[0]["ts"]) / 3600, 1e-9)
        rungs = Counter(e.get("rung") for e in log)
        lines.append(f"- Decisions: {len(log)} over {hours:.1f}h "
                     f"({len(log) / hours:.0f}/h); last {_ago(log[-1]['ts'], now)}")
        lines.append("- Rung distribution: " + ", ".join(
            f"{RUNG_NAMES.get(r, r)} {n} ({100 * n // len(log)}%)"
            for r, n in sorted(rungs.items())))
        plans = [e for e in log if "plan" in e]
        if plans:
            aborts = sum(1 for m in metrics if m.get("kind") == "plan_abort")
            avg_len = sum(len(e["plan"]) for e in plans) / len(plans)
            lines.append(f"- Plans: {len(plans)} multi-step (avg {avg_len:.1f} steps), "
                         f"{aborts} aborted mid-plan")
        top = Counter(e.get("behavior") for e in log).most_common(8)
        lines.append("- Top behaviors: " + ", ".join(f"{b} x{n}" for b, n in top))
        prompts = Counter(e["prompt"] for e in log if e.get("prompt"))
        if prompts:
            lines.append("- Prompt versions: " + ", ".join(
                f"{h} ({n} decisions)" for h, n in prompts.most_common()))
    else:
        lines.append("- No decisions logged yet.")
    saves = sum(1 for m in metrics if m.get("kind") in ("savestate", "ingame_save"))
    invalid = [m for m in metrics if m.get("kind") == "prompt_invalid"]
    lines.append(f"- Saves (ratchet): {saves}")
    if invalid:
        lines.append(f"- PROMPT REJECTED {len(invalid)}x — latest: "
                     f"{invalid[-1].get('detail', '?')} (fix prompts/<game>/prompt.md!)")
    lines.append("")

    # -- milestones -----------------------------------------------------------
    lines.append("## Milestones (RAM changes: badges, map, party)")
    stones = [m for m in metrics if m.get("kind") == "milestone"]
    for m in stones[-10:]:
        changed = {k: v for k, v in m.items() if k not in ("ts", "kind")}
        lines.append(f"- {_ago(m['ts'], now)}: {changed}")
    if stones:
        lines.append(f"- (!) Time since last milestone: {_ago(stones[-1]['ts'], now)}")
    else:
        lines.append("- none recorded")
    lines.append("")

    # -- escalations ----------------------------------------------------------
    open_esc = [e for e in escalations if not e.get("resolved")]
    lines.append(f"## Escalations ({len(open_esc)} open / {len(escalations)} total)")
    for e in open_esc[-5:]:
        lines.append(f"- {_ago(e['ts'], now)} [{e.get('kind')}] {e.get('detail')}"
                     + (f" — snapshot: {e['snapshot']}" if e.get("snapshot") else ""))
    lines.append("")

    # -- current beliefs and strategy ------------------------------------------
    memory = (run_dir / "memory.md")
    lines.append("## Gemma's current notes (memory.md — verify against snapshots)")
    lines.append(memory.read_text(encoding="utf-8").strip() if memory.is_file()
                 else "(empty — Gemma has written no notes)")
    lines.append("")
    goals = (run_dir / "goals.md")
    lines.append("## Current goals.md")
    lines.append(goals.read_text(encoding="utf-8").strip() if goals.is_file()
                 else "(missing!)")
    lines.append("")

    # -- recent activity + evidence pointers -----------------------------------
    lines.append("## Last 15 decisions (oldest first)")
    for e in log[-15:]:
        why = f' — "{e["reason"]}"' if e.get("reason") else ""
        plan = f" [plan {e.get('executed')}/{len(e['plan'])}]" if e.get("plan") else ""
        lines.append(f"- {RUNG_NAMES.get(e.get('rung'), '?')}: "
                     f"{e.get('behavior')}{plan}{why}")
    lines.append("")
    snaps = sorted((run_dir / "snapshots").glob("*.png"))
    lines.append("## Evidence")
    lines.append(f"- Newest snapshots: "
                 + (", ".join(s.name for s in snaps[-3:]) if snaps else "none"))
    lines.append(f"- Full detail: log.jsonl ({len(log)} entries), "
                 f"metrics.jsonl ({len(metrics)}), profile snapshot: profile.yaml")
    return "\n".join(lines) + "\n"


def write_briefing(run_dir: Path) -> Path:
    out = run_dir / "briefing.md"
    out.write_text(build_briefing(run_dir), encoding="utf-8")
    return out


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m harness.briefing <run-dir>")
        raise SystemExit(2)
    path = write_briefing(Path(sys.argv[1]))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
