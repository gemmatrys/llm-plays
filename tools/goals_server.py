"""Tiny read-only viewer for the run's CURRENT goal/quest.

Standalone on purpose: separate process, separate port, so it survives
harness restarts and can be pointed at any run dir. Reads the strategy
file fresh on every request — no caching, no watching. Quest-era runs
(quests.yaml present) render the current quest via QuestBook; legacy
runs fall back to goals.md parsing.

    python tools/goals_server.py --run-dir runs/pokemon_red/<id> --port 8702
"""
from __future__ import annotations

import argparse
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from harness.quests import QuestBook
except Exception:  # noqa: BLE001 — viewer must run even if harness moves
    QuestBook = None

PAGE = """<!doctype html><meta charset="utf-8"><title>current goal</title>
<style>
  body { background:#111; color:#eee; font:20px/1.45 system-ui,sans-serif;
         margin:0; padding:24px; }
  #num { color:#e8b339; font-size:15px; letter-spacing:.12em;
         text-transform:uppercase; margin-bottom:8px; }
  #txt { white-space:pre-wrap; max-width:52em; }
</style>
<div id="num"></div><div id="txt">loading…</div>
<script>
async function tick() {
  try {
    const r = await fetch('/goal.txt', {cache: 'no-store'});
    const t = await r.text();
    const nl = t.indexOf('\\n');
    document.getElementById('num').textContent = nl < 0 ? '' : t.slice(0, nl);
    document.getElementById('txt').textContent = nl < 0 ? t : t.slice(nl + 1);
  } catch (e) {}
  setTimeout(tick, 3000);
}
tick();
</script>"""


def current_goal(md: str) -> tuple[str, str]:
    """(label, text) of the first numbered goal not stamped [DONE].
    Blocks start at a line like "8. ..." and end at the next numbered
    line or the Rules: section."""
    blocks: list[tuple[str, str]] = []
    cur_num, cur_lines = None, []
    for line in md.splitlines():
        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m:
            if cur_num is not None:
                blocks.append((cur_num, "\n".join(cur_lines).strip()))
            cur_num, cur_lines = m.group(1), [m.group(2)]
        elif re.match(r"^Rules\s*:", line):
            break
        elif cur_num is not None:
            cur_lines.append(line.strip())
    if cur_num is not None:
        blocks.append((cur_num, "\n".join(cur_lines).strip()))
    for num, text in blocks:
        if "[DONE]" not in text.split("\n", 1)[0]:
            return f"goal {num}", text
    if blocks:
        return "all goals done", "waiting for the checkpoint to write the next stretch"
    return "no goals", "goals.md has no numbered goals"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--port", type=int, default=8702)
    args = ap.parse_args()
    goals_path = Path(args.run_dir) / "goals.md"
    quests_path = Path(args.run_dir) / "quests.yaml"

    def read_current() -> tuple[str, str]:
        if QuestBook is not None and quests_path.is_file():
            qb = QuestBook(quests_path)
            cur = qb.current()
            if cur is not None:
                n, act, q = cur
                label = f"quest {n} — {act.get('title', '')}"
                text = q.get("text", "").rstrip()
                if q.get("done"):
                    text += f"\nDONE when {q['done'].rstrip()}."
                return label, text
            if qb.active:
                return "all quests done", "the game is over (or the tree is)"
        return current_goal(goals_path.read_text(encoding="utf-8"))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 — stdlib naming
            if self.path.startswith("/goal.txt"):
                try:
                    label, text = read_current()
                    body = f"{label}\n{text}".encode()
                except OSError:
                    body = b"strategy file unavailable\n"
                ctype = "text/plain; charset=utf-8"
            else:
                body = PAGE.encode()
                ctype = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):  # quiet
            pass

    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
