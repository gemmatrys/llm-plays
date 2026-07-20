# Learnings — Phase 2 shakeout (gemma-run-1 and predecessors, 2026-07-19/20)

What the first real runs taught us. Most items are already encoded in code,
prompts, or config; this file is the narrative record so checkpoints and future
phases don't relearn them. Format: lesson → where it now lives.

## Model & serving

- **Served model name must match the harness `--model`.** A mismatch 404s every
  call and the ladder silently masks it. → `llm_failure` metric (watchdog
  callback) makes any rung-1 failure visible; CLI default is now `gemma`.
- **Gemma 4 thinking is off by default.** `--reasoning-parser gemma4` at serve
  time + `chat_template_kwargs {"enable_thinking": true}` per request
  (`reasoning_effort` is ignored by llm-scaler 0.21.0-b1). Thinking coexists
  with JSON-schema guided decoding. → llm.py `reasoning` option, default low.
- **The thinking transcript is currently unrecoverable** (vllm#38855: parser
  strips channel tokens; `reasoning_content` comes back empty). The full
  pipeline for it (log field, overlay panel) is wired and waits. → stream UI
  shows an explicit "(thinking channel not available yet)" placeholder.
- **Thinking starves under a tight token cap exactly when confused** — long
  reasoning eats max_tokens and `content` comes back None, so the hardest
  states produced no decision. → generous budget (1100), explicit error text,
  and HTTP timeout kept 10s BELOW the watchdog deadline so a slow request
  frees the single policy worker before the next queues (pileups looked like
  multi-minute hangs; py-spy stack dump diagnosed it).
- **31B dense QAT: ~20 tok/s on the B70** → 20-30s thinking decisions. MoE
  26B-A4B (4B active) is the speed play; no official w4a16-ct exists for it
  (704-wide experts), so serve Google's QAT bf16 weights with llm-scaler
  `--quantization sym_int4 --dtype float16` (sym_int4 rejects bf16).
- Pause the harness during server swaps: **rung-2 fallback keeps playing
  through a brain outage**, which is the design working — but never let it
  mash through irreversible choices (starter selection, save prompts).

## Game knowledge (Gen 1)

- **The door trap**: exiting a building leaves you ON the doorstep; UP walks
  back in. → prompt.md rule + seed goals.
- **Pallet Town geography**: west edge is water (not walkable); the Route 1
  exit gap is at the top, around x=10; Oak's Lab is map 40, town is map 0,
  player's house 37/38. → seed goals route description.
- **Position context beats vision for navigation**: pos_x/pos_y from RAM
  (D362/D361) + map-transition markers `[entered map N]` in the recent-actions
  list made door loops and wall-pushing visible to the model. → profile
  ram_map + loop.py markers.
- **A-mash is the game's default gravity; goals should list exceptions, not
  steps.** Battle cursor defaults to FIGHT; naming screens are the trap
  (fallback-era mashing named the player "AA").

## Harness & ops

- **One universal scripted fallback is wrong** — mash_a in the overworld
  presses A at walls forever. → `scripted_fallback` is a rotated list
  (interact + all four directions).
- **Every outage class needs its own alarm**: brain (llm_failure), eyes/hands
  (driver_down escalation after 5 consecutive tick errors + backoff),
  harness itself (external heartbeat on log mtime; console.log captures
  crashes). Silent degradation cost a debug cycle each time before these.
- **The driver must drop dead sockets** (any OSError → reconnect next call),
  or an emulator restart wedges the loop forever.
- **The recovery drill works**: driver_down → restore emulator+bridge →
  loadstate slot 1 (ratchet keeps loss <5 min) → checkpoint-refresh goals to
  match the restored position → relaunch. Ran twice, routine by the second.
- **Checkpoint edits to the run's goals.md are the highest-leverage unstick
  tool** — three door/corner rescues came from goals rewrites, live within
  one decision.

## Windows-specific

- Files crossing to the Linux box need CRLF **and BOM** scrubbing (PS 5.1
  `Set-Content -Encoding utf8` writes a BOM that breaks shebangs); write with
  `UTF8Encoding($false)` + LF, or sed both on arrival.
- PowerShell 5.1 mangles quoted inline scripts → anything non-trivial goes
  through a staged script file. `Get-Process` lacks CommandLine — use CIM to
  target processes; killing "the" python needs it (each launch is shim+real).
- Hyper-V reserves shifting port ranges (bit 8600 AND later 8611) —
  `netsh int ipv4 show excludedportrange tcp` before picking service ports.
- Piping installers through `tail`/`head` masks exit codes and can SIGPIPE
  the script mid-run — log to a file, check RESULT markers.

## Metrics reality (for the essay)

- Validation-probe latency (1.1s) ≠ in-harness latency (3-5s instinct,
  20-35s thinking): real prompts carry image + goals + notes + history.
- Plans amortize hard: 8/8 executions during overworld walking ≈ 3.5s/action
  even with 28s decisions; plan aborts cluster exactly where they should
  (map transitions, dialogue).
- The fish's chaos has a long tail: it named the player "AA" and once walked
  INTO the game from the title screen in 10 seconds.
