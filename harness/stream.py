"""Live telemetry overlay: what Gemma is thinking, on screen.

The harness updates a shared StreamState every tick; a tiny HTTP server exposes
- /            an OBS-friendly overlay page (add as a Browser Source; the page
               background is transparent so it composites over gameplay)
- /state.json  the raw state, for anything else (widgets, bots, post-analysis)

Gameplay video itself is OBS capturing the emulator window; this page is the
"thinking" side panel next to it. Thoughts are also permanently recorded in
log.jsonl (the Decision.reason field), so the stream shows exactly what the log
stores.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class StreamState:
    """Thread-safe snapshot of 'what the system is doing right now'."""

    def __init__(self, game: str = "", policy: str = ""):
        self._lock = threading.Lock()
        self._d = {
            "game": game,
            "policy": policy,
            "started_ts": time.time(),
            "decisions": 0,
            "behavior": "",
            "rung": 0,
            "thought": "",
            "generating": False,  # True while the policy is streaming thinking
            "goals": "",
            "ram": {},
            "rung_counts": {},
            "escalations": 0,
            "savestates": 0,
            "recent": [],  # last N {ts, behavior, rung, thought}
        }

    def push_decision(self, behavior: str, rung: int, thought: str,
                      ram: dict | None, goals: str, memory: str = "",
                      thinking: str = "") -> None:
        with self._lock:
            d = self._d
            d["decisions"] += 1
            d["behavior"] = behavior
            d["rung"] = rung
            d["thought"] = thought
            d["goals"] = goals
            d["memory"] = memory
            d["thinking"] = thinking
            d["generating"] = False
            d["ram"] = ram or {}
            d["rung_counts"][str(rung)] = d["rung_counts"].get(str(rung), 0) + 1
            d["recent"].append({"ts": time.time(), "behavior": behavior,
                                "rung": rung, "thought": thought})
            del d["recent"][:-12]

    def stream_thinking(self, text: str, done: bool = False) -> None:
        """Live push of the (growing) thinking transcript from the policy, so the
        overlay streams it token by token; done=True marks generation finished."""
        with self._lock:
            self._d["thinking"] = text
            self._d["generating"] = not done

    def bump(self, counter: str) -> None:
        with self._lock:
            self._d[counter] = self._d.get(counter, 0) + 1

    def to_json(self) -> bytes:
        with self._lock:
            d = dict(self._d)
        d["uptime_s"] = round(time.time() - d["started_ts"])
        hours = max(d["uptime_s"] / 3600, 1e-9)
        d["decisions_per_hour"] = round(d["decisions"] / hours, 1)
        return json.dumps(d).encode()


def start_server(state: StreamState, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 — http.server API
            if self.path.startswith("/state.json"):
                body, ctype = state.to_json(), "application/json"
            elif self.path == "/" or self.path.startswith("/index"):
                body, ctype = OVERLAY_HTML.encode(), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # keep the console quiet
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True,
                     name="stream-server").start()
    return server


RUNG_LABELS = {1: "GEMMA", 2: "SCRIPT", 3: "IDLE", 4: "FISH"}

OVERLAY_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>llm-plays overlay</title><style>
  :root { --fg:#e8e8f0; --dim:#9aa0b4; --gemma:#7ee787; --script:#79c0ff;
          --idle:#d2a8ff; --fish:#ffa657; }
  body { background: transparent; color: var(--fg); margin: 0;
         font: 15px/1.45 "Segoe UI", system-ui, sans-serif; }
  #panel { background: rgba(10,12,20,.82); border-radius: 12px; padding: 14px 16px;
           max-width: 420px; }
  #head { display:flex; justify-content:space-between; align-items:baseline; }
  #game { font-weight: 700; letter-spacing:.4px; }
  #up { color: var(--dim); font-size: 12px; }
  #rung { display:inline-block; font-weight:700; font-size:12px; padding:1px 8px;
          border-radius:9px; margin-right:8px; color:#0b0d14; }
  .r1{background:var(--gemma)} .r2{background:var(--script)}
  .r3{background:var(--idle)} .r4{background:var(--fish)}
  /* the chosen move is hidden while the reasoning types out, then fades in —
     the broadcast beat is "watch it think, THEN see what it decided". */
  #decision { margin-top:10px; transition:opacity .5s ease; }
  #decision.pending { opacity:.1; }
  #pressed { font-size:12px; color:var(--dim); }
  #behavior { display:block; font-size:19px; font-weight:700; color:var(--fg);
              letter-spacing:.3px; }
  .label { margin-top:10px; font-size:11px; letter-spacing:.12em;
           text-transform:uppercase; color:var(--dim); }
  /* bounded "stream of thought": fixed window, newest at the bottom, older
     lines scroll up and fade under the top mask. Without the height cap a long
     transcript (now real — up to ~2k chars) would blow up the whole overlay. */
  #thinking { height:7.2em; font-size:14px; color:var(--fg); opacity:.97;
              overflow:hidden; white-space:pre-wrap; word-break:break-word;
              -webkit-mask-image:linear-gradient(to bottom,transparent 0,#000 1.5em);
              mask-image:linear-gradient(to bottom,transparent 0,#000 1.5em); }
  #thinking.offline { height:auto; color:var(--dim); font-style:italic;
              opacity:.7; -webkit-mask-image:none; mask-image:none; }
  #why { font-size:14px; color:var(--fg); margin-top:2px; }
  #why:empty { display:none; }
  #why::before { content:"\\201C"; color:var(--dim); }
  #why::after  { content:"\\201D"; color:var(--dim); }
  #notes { min-height:2.4em; font-size:14px; }
  #stats { display:grid; grid-template-columns:repeat(4,1fr); gap:6px;
           text-align:center; font-size:12px; color:var(--dim); margin-top:10px; }
  #stats b { display:block; font-size:16px; color:var(--fg); }
  #feed { margin-top:10px; font-size:12px; color:var(--dim); max-height:8em;
          overflow:hidden; }
  #feed div { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
</style></head><body>
<div id="panel">
  <div id="head"><span id="game">–</span><span id="up">–</span></div>
  <div class="label">thinking</div>
  <div id="thinking" class="offline">warming up…</div>
  <div id="decision" class="pending">
    <div id="pressed"><span id="rung" class="r4">–</span>pressed
      <span id="behavior">…</span></div>
    <div id="why"></div>
  </div>
  <div class="label">notes</div>
  <div id="notes">–</div>
  <div id="stats">
    <span>decisions<b id="n">0</b></span>
    <span>per hour<b id="dph">0</b></span>
    <span>badges<b id="badges">–</b></span>
    <span>escalations<b id="esc">0</b></span>
  </div>
  <div id="feed"></div>
</div>
<script>
const LBL = {1:"GEMMA",2:"SCRIPT",3:"IDLE",4:"FISH"};
let curDecision = -1;
function revealDecision(s) {
  const el = id => document.getElementById(id);
  el("rung").textContent = LBL[s.rung] || "–";
  el("rung").className = "r" + (s.rung || 4);
  el("behavior").textContent = s.behavior || "…";
  el("why").textContent = s.thought || "";
  el("decision").classList.remove("pending");
}
async function tick() {
  try {
    const s = await (await fetch("/state.json")).json();
    const el = id => document.getElementById(id);
    el("game").textContent = s.game + "  ·  " + s.policy;
    const h = Math.floor(s.uptime_s/3600), m = Math.floor(s.uptime_s%3600/60);
    el("up").textContent = h + "h " + String(m).padStart(2,"0") + "m";
    // stream the model's reasoning straight into the DOM as it generates — no
    // fake typewriter; the text IS the live server output growing token by token.
    const th = document.getElementById("thinking");
    if (s.thinking) { th.className = ""; th.textContent = s.thinking;
                      th.scrollTop = th.scrollHeight; }
    else { th.className = "offline"; th.textContent = "warming up…"; }
    // reveal the move only once a new decision is committed (stream finished and
    // plan executed); keep it hidden while the model is still generating.
    if (s.decisions !== curDecision) { curDecision = s.decisions; revealDecision(s); }
    else if (s.generating) { el("decision").classList.add("pending"); }
    el("notes").textContent = s.memory || "–";
    el("n").textContent = s.decisions;
    el("dph").textContent = s.decisions_per_hour;
    el("badges").textContent = (s.ram && "badges" in s.ram) ? s.ram.badges : "–";
    el("esc").textContent = s.escalations;
    el("feed").innerHTML = (s.recent || []).slice(0,-1).reverse().map(r =>
      "<div>" + (LBL[r.rung]||"?") + " " + r.behavior +
      (r.thought ? " — " + r.thought : "") + "</div>").join("");
  } catch (e) { /* harness restarting; keep polling */ }
}
setInterval(tick, 250); tick();  // fast poll so streamed thinking looks live
</script></body></html>
"""
