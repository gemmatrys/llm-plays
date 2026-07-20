# llm-plays

Autonomous game-playing: a local LLM picks behaviors, a watchdog guarantees liveness,
Claude checkpoints handle strategy. See [PLAN.md](PLAN.md) for the architecture,
[INSTALL.md](INSTALL.md) for machine setup, [PRESENTATION.md](PRESENTATION.md) for the
talk-track version.

## Quick start (Phase 1: fish plays Pokémon Red)

1. `pip install -e .`
2. Launch the emulator: `powershell emulator\launch_mgba.ps1` (starts mGBA in
   GBC mode, borderless; pass `-Rom <path>` for other games), then the one
   manual step — Tools → Scripting → load
   [emulator/mgba_bridge.lua](emulator/mgba_bridge.lua)
   (console should say `llm-plays bridge listening on port 8765`).
3. ```
   python -m harness --profile profiles/pokemon_red.yaml --policy fish
   ```
4. Watch `runs/pokemon_red/<run-id>/` fill up: `log.jsonl` (every decision),
   `metrics.jsonl` (saves, escalations), `snapshots/` (periodic PNGs).

`--policy llm --endpoint http://<arc-box>:8000` switches rung 1 to the local model
(Phase 2). `--policy none` runs pure fallback-ladder (watchdog test).

## Streaming (what Gemma is thinking, on screen)

The harness serves a live overlay at `http://127.0.0.1:8700/` (`--stream-port`,
0 disables; avoid 8563-8662, which Windows reserves for Hyper-V). OBS setup:

1. **Game Capture / Window Capture** → the mGBA window (the gameplay).
2. **Browser Source** → `http://127.0.0.1:8700/`, ~440×360. Transparent background;
   shows the current thought, chosen behavior, which ladder rung is in control
   (GEMMA / SCRIPT / IDLE / FISH), badges, decisions/hour, escalations, and a feed
   of recent thoughts.

`/state.json` exposes the same data for bots or custom widgets. Every thought shown
is also permanently recorded in `runs/.../log.jsonl` (the `reason` field), so stream
and record never disagree.

## Layout

```
harness/            the Python package (loop, watchdog, executor, policies, drivers)
emulator/           mGBA Lua bridge script
profiles/           per-game YAML config (buttons, ladder, ratchet, RAM map)
skills/             behavior library — grows over time, partly Claude-authored
runs/               per-run state: goals.md, logs, metrics, escalations, snapshots
```

## Status

Phase 1 scaffold. Untested against a live mGBA yet — the Lua bridge and the mGBA
driver are the first things to validate (Phase 0 exit criteria in PLAN.md §7).
