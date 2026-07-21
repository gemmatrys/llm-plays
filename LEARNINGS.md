# Learnings — Phase 2 shakeout (gemma-run-1 and predecessors, 2026-07-19/20)

What the first real runs taught us. Most items are already encoded in code,
prompts, or config; this file is the narrative record so checkpoints and future
phases don't relearn them. Format: lesson → where it now lives.

## Model & serving — QAT vs base+online-quant (2026-07-20)

- **Every QAT/pre-quantized checkpoint hit an untested XPU kernel path and
  crashed on first inference** on `intel/llm-scaler-vllm:0.21.0-b1`: the 12B
  `w4a16-ct` (compressed-tensors) throws `k_descale must be a scalar tensor` in
  FlashAttention; the 26B-A4B MoE (`q4_0-unquantized`, sym_int4) throws
  `Expected logits.scalar_type() == torch::kHalf` in the fused-MoE router
  (`moe_topk`). Neither is fixable from outside the container — no serve flag
  changes it (`--kv-cache-dtype float16/bfloat16` both rejected at init for the
  12B too). → serving those models is a dead end on this llm-scaler build.
- **The fix: serve the BASE `-it` models with ONLINE quantization** — the
  llm-scaler README's actually-documented, Intel-tested path
  (`--quantization fp8` or `sym_int4`, plus `--dtype float16
  --mamba-ssm-cache-dtype float16 --block-size 64`). `google/gemma-4-12B-it`
  with `fp8` passes full validation (text/vision/JSON) AND thinking — no
  kernel crash. → `server/serve_gemma.sh` auto-selects fp8 for any `*-it` model.
- **Online quant does NOT avoid the load-time RAM problem** — it still stages
  the full bf16 checkpoint before quantizing, so a 26B+ model needs either a
  big RAM/VRAM box or swap. `VLLM_OFFLOAD_WEIGHTS_BEFORE_QUANT=1` only helps
  the quantize step, not the initial mmap/load. `vm.overcommit_memory=1` +
  ~75GB swap on the box's SATA SSD (root fs) fixed the mmap ENOMEM and let the
  MoE fully load — but it still hit the moe_topk crash on first inference, so
  swap was necessary-but-not-sufficient for the MoE.
- **Quant-speed ladder measured** (32GB B70, mem-util 0.9): 12B sym_int4 ~40
  tok/s thinking but vision garbles text (4-bit degradation, saw "Pok?mone");
  12B fp8 ~35 tok/s with clean vision (recommended fast pick); 31B w4a16-ct
  ~20-22 tok/s, best quality (chosen for the actual benchmark run). KV pools:
  12B fp8=373,243 tok (native 262144 ctx now binds, not VRAM); 31B=38,302 tok.
- **Context window: MAXLEN is free to raise, up to the KV pool** —
  `--max-model-len` doesn't reserve extra VRAM (that's `gpu-memory-util`'s
  job), it only caps tokens/request. Policy: serve ceiling = ~95% of the
  model's measured KV pool ("GPU KV cache size" in the log); the harness's
  actual prompt-building stays far under that (a separate, deliberate
  discipline, not a hard limit) — `serve_gemma.sh`'s `MAXLEN` env, re-derive
  per model.
- **Timing relaxed to aim-120/enforce-15 decisions per hour**
  (`decision_cadence_s=30`, `ladder.llm_timeout_s=240`, thinking
  `max_tokens=1100→4000`) — the tighter 60s/1100-token config from the first
  shakeout was too tight for a 31B thinking through a real prompt.

## Thinking transcript — two different fixes for two different code paths

- **Non-streaming replies**: `reasoning_content` is ALWAYS empty on this
  llm-scaler build — the detokenizer strips `<|channel>…<channel|>` markers
  regardless of `skip_special_tokens` (vllm#38855; PR #39027's
  `adjust_request` is present in this build but doesn't fix it here). The
  markers DO survive in the non-streaming `logprobs` token array, so they can
  be reconstructed by splitting on the delimiters — this was the first fix,
  now unused in the live path (see below) but documented as a fallback fact.
- **Streaming replies sidestep the whole problem**: `stream:true` requests
  return clean, incremental `delta.reasoning` chunks directly — even under
  guided JSON — with no stripping at all. `llm.py`'s `decide()` now always
  streams when reasoning is on; this is strictly simpler and is what actually
  ships. Verified live: hundreds of growing chunks over ~10-20s ending in a
  valid plan, non-thinking path unaffected.
- **Fake "typewriter" reveal was wrong** — animating an already-complete reply
  meant the button press effectively happened before the reasoning appeared
  on stream. Real streaming (server chunks pushed into `StreamState` via
  `policy.on_stream`, DOM updated every 250ms poll) fixes this structurally:
  the plan is only parsed/acted on after the stream finishes, so "reasoning
  shown" and "reasoning done" are the same event. → `harness/stream.py`,
  `harness/policy/llm.py`.

## ASCII map context — ground-truth RAM beats vision AND naive tile dumps

- **Bulk-reading the screen tilemap needs a driver primitive** the emulator
  didn't have — added `READBLOCK <addr> <len>` to `mgba_bridge.lua`
  (`emu:readRange`) + `MGBADriver.read_block`. One round-trip vs N `READ8`s.
  Requires the user to reload the Lua script in mGBA once (Tools→Scripting) —
  no live-reload API exists.
- **Walkable tile-ID sets are per-TILESET, not universal** — the seeded
  overworld set rendered an interior room's floor as blocked and its walls as
  open (exactly inverted: indoor floor 0x01 isn't in the overworld set, indoor
  wall 0x00 is). FIXED 2026-07-20: `walkable_by_tileset` in the profile, keyed
  by wCurMapTileset (0xD367, one extra READBLOCK per tick); tileset 0
  (overworld) and 1 (Red's house — floor 0x01 only) verified live. A tileset
  with no entry degrades to the raw-id dump WITH the tileset id in the header,
  so a logged dump is attributable — the harvesting workflow for each new
  tileset is: stand in the room, read the dump, mark open tiles against the
  screenshot, add the entry.
- **Walkability is per-BLOCK, judged by the block's BOTTOM-LEFT subtile** —
  Gen 1's own collision convention. Classifying each 8x8 subtile against the
  collision list renders mixed blocks wrong: overworld flower ground (2c/03
  mixed, bottom-left 2c) drew a checkerboard of phantom walls on Route 1.
  Fixed 2026-07-20: the renderer classifies each 2x2 block by its bottom-left
  id, which makes pokered's per-tileset collision lists correct verbatim.
  Terrain now lives in `data/<game>/tiles.yaml` (walkable + portal ids per
  tileset) — a HOT file checkpoints extend live (no restart), validated with
  last-good fallback + tiles_invalid escalation. Harvest drill: read the
  BOTTOM-LEFT corner of each block in the tagged raw dump.
- **Warp/portal coordinates are Gen 1's `(y, x, destWarp, destMap)`, NOT
  `(x, y, ...)`** — got this backwards once and it put the door marker on the
  bed instead of the stairs. Confirmed by walking the player onto the real
  stairs and reading its exact warp-table bytes at that instant; ground-truth
  a coordinate system by producing an actual transition, don't reason about it
  in the abstract. → `harness/loop.py::_read_tilemap`.
- **Off-map tiles must render blocked explicitly** — reading `wCurMapHeight`/
  `wCurMapWidth` and marking anything beyond them `#` stops the model from
  ever thinking it can walk into the border void.
- **The portal marker + a relative-direction summary line (not just the grid)
  is what actually helps** — "You are not on an exit. Exits: 2 left." answers
  both "am I on a portal" and "which way do I walk" using only reliable RAM
  (player pos + warp table), independent of the still-imperfect walkability
  tileset data.

## Behaviors: step_factory for randomization, and the fish should DO things

- **A fixed-sequence "mash" behavior can get wedged** on a specific text
  speed or a yes/no prompt stuck on YES. Added `Behavior.step_factory`
  (executor calls it fresh each run instead of using static `.steps`) so
  `mash_through_dialogue` regenerates a randomized A/B sequence every
  invocation — this alone let a run escape a state that looked wedged across
  16 decisions in the previous (fixed-sequence) build.
- **Fish/rung-4 jittering one random button is nearly useless** — it doesn't
  explore. Replaced with `fish_move`, a random dispatcher over a REAL
  repertoire (`wander`, `mash_through_dialogue`, mash-a-direction, mash-B,
  `get_unstuck`, press-any), shared by `FishPolicy` and the ladder's rung 4.
  Seeded rng keeps calibration runs reproducible.
- **`get_unstuck`** (random presses across ALL buttons, 5-9 taps) is the
  "nothing else worked" escape hatch — Gemma-selectable AND in the fish
  repertoire. In practice the run escaped its stuck state through NORMAL play
  once the prompt fix landed (see below), so this stayed an unused backstop —
  which is fine; it's insurance, not the primary mechanism.
- **A-mashing should be SHORT and BURSTY, not long-held/widely-spaced** —
  rapid taps in quick succession clear dialogue and confirm
  menus/naming-screens fastest. Tightened `mash_a` (16→10 frames/press) and
  `mash_through_dialogue` (avg ~26→ shorter, tighter bursts).

## Model & serving

- **Served model name must match the harness `--model`.** A mismatch 404s every
  call and the ladder silently masks it. → `llm_failure` metric (watchdog
  callback) makes any rung-1 failure visible; CLI default is now `gemma`.
- **Gemma 4 thinking is off by default.** `--reasoning-parser gemma4` at serve
  time + `chat_template_kwargs {"enable_thinking": true}` per request
  (`reasoning_effort` is ignored by llm-scaler 0.21.0-b1). Thinking coexists
  with JSON-schema guided decoding. → llm.py `reasoning` option, default low.
- **The thinking transcript is recovered from logprobs** (2026-07-20). On the
  llm-scaler XPU build `reasoning_content` comes back empty because the
  detokenizer strips the `<|channel>…<channel|>` markers regardless of
  skip_special_tokens (vllm#38855) — BUT the per-token `logprobs` stream keeps
  them verbatim. So `llm.py` requests `logprobs:true` when thinking is on and
  rebuilds the transcript by splitting on the delimiters
  (`_thinking_from_logprobs`); the answer JSON still arrives clean in `content`,
  so plan parsing is untouched. The overlay/runlog pipeline that was "wired and
  waiting" now shows real chain-of-thought. Verified end-to-end through
  LLMPolicy against the live 31B.
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
  steps.** Battle cursor defaults to FIGHT. The fallback-era "AA" naming
  incident was NOT actually a problem worth avoiding — mashing A on the
  naming screen just confirms whatever preset name is highlighted and moves
  on, and the exact name never matters. An earlier version of this project's
  own prompt.md over-corrected on this (called the naming screen a "TRAP",
  told the model never to mash A there) which CONTRADICTED goals.md's
  original, correct instruction and likely caused indecision rather than
  helping. Corrected 2026-07-20: prompt.md now says mash_a is fine there; the
  scripted_fallback rotation keeps press_B (generically useful for menus, not
  naming-specific) so a brain outage still has an escape option.
- **B does NOT exit the Gen 1 letter grid** — it only deletes typed letters
  (with none typed it does nothing). The earlier prompt.md claim "B backs out
  to the preset list" was wrong and wedged `limits-4` in a B/DOWN/A loop on
  the naming grid for ~15 min (model dutifully followed the false fact every
  decision; rung 1 healthy throughout, so no alarm fired — and the stagnation
  monitor was NOT closing in: each cycle typed/deleted different letters at
  drifting cursor positions, minting novel phash variants that kept resetting
  the 20-min novelty timer. Progress-free novelty is a stuckness-detector
  blind spot; see the stuckness callouts). Correct escape:
  A (type any letter), START (cursor jumps to ED), A (confirm) — verified
  live, the wedged run escaped within two decisions of the hot prompt/goals
  edit. Lesson: game-mechanics claims in prompt.md are load-bearing; ground
  them like the warp coordinates (produce the actual transition once) instead
  of asserting from memory. → prompt.md Screens bullet + goals seed. Lesson: when
  a rare bad outcome is actually harmless (name doesn't matter), don't build
  prompt rules around avoiding it — check what the goal actually cares about
  before treating a symptom as a problem.

## Context & prompting economics (2026-07-20, from thinking transcripts)

- **Latency scales with what the model must INFER or reconcile, not with
  context volume.** KV cache sat at 13% while decisions took 124s: the tokens
  went into re-litigating ambiguity (goals-vs-prompt contradictions, geometry
  it couldn't resolve). Clear goals dropped the same model to 20-38s
  instantly. Feed CONCLUSIONS, not raw material: in_battle flag, N markers
  for NPCs, [move blocked] feedback — each replaced an inference class.
  → context_ram_map, sprite overlay, wall feedback (harness/loop.py).
- **Stale guidance is worse than no guidance.** Three separate slow-downs
  traced to finished or obsolete instructions still in goals/memory (lab
  directions on Route 1, pocket-escape advice after escaping). Fixes:
  `done_goal` (the model stamps finished goals [DONE] itself), goals under
  the 200-word budget, checkpoints prune at rewrite, and a >90s
  slow-decision watcher because long thinking IS the confusion alarm.
- **Never make the model do spatial search** — route "calculation" in
  thinking was 90-124s per decision; navigation macros (walk_<dir> /
  walk_to_exit, BFS on the map grid, harness/navigate.py) dropped the same
  situations to 14-18s with four tiles of progress per decision. The pattern
  generalizes: any deterministic computation the model performs in tokens is
  a behavior the harness should perform in code — the model picks WHAT, the
  harness computes HOW.
- **Prompt philosophy: encourage trial and error.** The game is
  fish-beatable and the ratchet makes mistakes cheap — so the prompt now
  says EXPERIMENT, don't deliberate; break loops on purpose. Prescriptive
  rule-lists made the model reason ABOUT rules instead of probing the world.
  The one guarded class stays guarded: confirmation yes/no prompts.
- **The checkpoint layer may use the web** (walkthroughs, wikis) when
  authoring goals/skills — declared in BENCHMARKS; knowledge lands in
  git-tracked files; Gemma itself never browses (per-decision latency is
  the whole game).

## The Charmander incident (2026-07-20) — irreversible choices vs mashing

- **A dialogue mash committed an irreversible choice**: the model pressed A on
  Charmander's pokeball (correctly, to inspect), then chose
  mash_through_dialogue on Oak's confirmation — a mid-burst A answered YES
  before the trailing B could decline. Party: CHARMANDER, nickname "A",
  permanent. The trailing-B design only guarantees the burst's END state;
  nothing inside the burst is safe on a confirmation prompt. → prompt.md +
  goals now forbid mashing on any yes/no confirming a specific choice
  (take/buy/learn/nickname): ONE press, A or B, per goals.
- **The single-slot ratchet cannot undo anything**: the pre-choice savestate
  (17:45:21) was 30 s older than the acceptance (17:45:51) and had been
  overwritten three times before anyone looked. Pending improvement: keep a
  second slot pinned at the last milestone so "just before something
  irreversible happened" survives longer than one ratchet interval.
- **The model then wedged on a FALSE BELIEF, and I3 worked end-to-end**: it
  opened party/stats menus convinced it still had to pick Bulbasaur ("Choose
  a POKeMON" = party menu, misread as the gift choice — prompt.md now says
  so). The behavior-loop detector self-rescued at +12 min, the position
  detector escalated at +17 min, and a checkpoint rewrite of the run's
  goals.md + memory.md redirected it within ONE decision (again the
  highest-leverage unstick tool). Escalation resolved in escalations.jsonl.

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
