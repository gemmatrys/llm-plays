# Learnings — Phase 2 shakeout (gemma-run-1 and predecessors, 2026-07-19/20)

What the first real runs taught us. Most items are already encoded in code,
prompts, or config; this file is the narrative record so checkpoints and future
phases don't relearn them. Format: lesson → where it now lives.

LOAD-BEARING INDEX (one line per section, for checkpoints under alarm
pressure — the full accounts are below, in chronological order):
- Model & serving: serve base `-it` models with online quant; MAXLEN is free
  up to the KV pool; thinking needs streaming.
- ASCII map (retired): collision is per-tileset, per-block bottom-left; warp
  coords are (y,x); ground-truth coordinate systems by producing a transition.
- Behaviors/fish: randomized bursts beat fixed sequences; mash short+bursty.
- Game knowledge: door trap; A-mash is gravity; ground mechanics claims live
  (the naming-grid B lie cost 15 min).
- Prompting economics: latency scales with what must be INFERRED — feed
  conclusions; stale guidance is worse than none; never make the model do
  spatial search; encourage trial and error.
- Charmander incident: never mash a committing yes/no; second savestate slot.
- Harness & ops: every outage class needs its own alarm; goals-file edits are
  the highest-leverage unstick tool; verify-every-step restarts.
- Doors & grounding: walks stop beside doors; false stamps are routine —
  validate against RAM; the harness must count/attest (bag events, visit
  counters); force stale-notes rewrites at the decoder.
- Attestation suite: place/bag/party/bearings/battle_hint — grounded context
  beats taught rules.
- Skills thesis: wire POSITIONING and fixed geometry, keep conversations with
  the model under the choice-stop guard; warp tables lie about enterability.
- Conflict economics: inapplicable rules cost +47% latency — rule-silencing
  lines and yield clauses; battle menus are geometry (attack_N skills);
  tripwire-judge; trajectory detectors (the model cannot see its own loop).
- Sentences beat structure: no jargon anywhere the model reads; micro-goals
  with DONE lines; probe tiles after two failed prose fixes.
- Cleanup & quest feed (2026-07-22): harness ingests the checkpoint-authored
  quest tree; prune ban-laden behaviors; fetch data, don't recall it; state
  serving stays generic.

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
  was what actually helped** — "You are not on an exit. Exits: 2 left."
  answered both "am I on a portal" and "which way do I walk" from reliable RAM
  alone. RETIRED with the map removal (2026-07-21): the string is still built
  but no prompt placeholder renders it — the same information now reaches the
  model via can_move's "(through a doorway)" and bearings. Backlog: drop the
  dead render (keep the tilemap READ — it feeds _nav for BFS/can_move).

## Behaviors: step_factory for randomization, and the fish should DO things

- **A fixed-sequence "mash" behavior can get wedged** on a specific text
  speed or a yes/no prompt stuck on YES. Added `Behavior.step_factory`
  (executor calls it fresh each run instead of using static `.steps`) for
  randomized-per-invocation behaviors. (2026-07-21: mash_through_dialogue
  no longer uses this — it became the RAM-grounded advance_text op; the
  randomized burst survives only in the fish/rung-4 repertoire, where
  step_factory still applies.)
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

## Doors & goal grounding — limits-4 Viridian session (2026-07-20 evening)

- **An unharvested tileset makes every walk macro a silent no-op.**
  (Trimmed 2026-07-21 — superseded: collision lists are PRE-INGESTED
  from pokered and unmapped areas fall back to one direct press; see
  the skills-thesis section.)
- **Directional walks can never stop ON a door** — they take the farthest
  reachable block along the axis, so they route around or past buildings;
  the model orbited the Viridian Center for 8 decisions "aligning with the
  door". (walk_to_exit was the era's door-stopper; RETIRED 2026-07-22 —
  see the cleanup section. Doors are entered by a single press; rooms are
  left by walking onto the doormat plus one edge press.)
- **Map-edge doormats are invisible to BFS** (no off-map goal exists):
  exiting a room needs a single raw press toward the edge, or entering the
  mat block sideways. → goals rule; DONE since: walk_to_exit appends the
  final edge-press itself when the route reaches an edge warp.
- **done_goal's first live firings were FALSE** — it stamped "healed at
  the Pokemon Center" while wedged in a private house it had mistaken for
  the Center. After a no-evidence-no-stamp rule was added to the run's
  goals, the next stamp (the real heal, nurse goodbye observed) was
  correct. → rule belongs in the base prompt for run-2; stronger option:
  harness-side guard requiring a state change consistent with the goal.
- **Checkpoint guidance works in natural language** — "walk to the exit",
  "press A", "walk north" map fine; exact macro identifiers only need to
  exist in prompt.md's allowed-behaviors contract (the parser is
  exact-match, llm.py raises on unknown names). Run-2 candidate: a reply
  normalizer (spaces→underscores + synonyms) to drop even that.
- **Blind dialogue mashing is self-defeating at NPCs that re-greet**: the
  open-loop A/B burst overshoots the dialogue's end, and the leftover A
  presses (still facing the NPC) START THE CONVERSATION OVER — the model
  looped the nurse's entire heal cycle 10+ times, each pass reinforcing
  "I must finish this dialogue". The trailing-B trick can't save it; only
  not-pressing-after-close can. → mash_through_dialogue is now a
  RAM-grounded executor op (`advance_text`): press A only while
  wFontLoaded (0xCFC4 bit 0, live-verified 1↔0) says a text box is open,
  stop when a choice cursor (▶ tile 0xED anywhere in wTileMap) appears so
  the model answers choices deliberately, do nothing when no text is open.
  Bracketed feedback strings tell the model which way it ended. The menu
  RAM (wCurrentMenuItem/wMaxMenuItem) is STALE after menus close — useless
  as an open-menu signal; the on-screen cursor glyph is the honest one.
  wFontLoaded is OVERWORLD-ONLY: battles never set it (live-verified —
  font=0 with EXP text on screen), so battle text needs its own gate:
  in battle, press A until the menu cursor appears or in_battle drops.
  0xED cursor detection VERIFIED live 2026-07-21 — advance_text stopped
  exactly at the nurse's yes/no (the remaining hole was the plan runner
  continuing past the stop; see the skills-thesis section). The old
  blind burst survives only in the fish.
- **The model cannot identify repeated structures or verify its own event
  claims — the harness must count and attest**: it believed "I have the
  parcel" (never obtained), "I healed" (never healed), and re-entered the
  same wrong building without recognizing it. Fix has two halves. (1)
  GROUND-TRUTH ATTESTATION: the bag (wNumBagItems/wBagItems) renders into
  the {ram} view as `bag=` and diffs into "[bag: +1 OAK'S PARCEL
  (game-verified)]" events — prompt teaches "no bag event = it did not
  happen"; item names in HOT data/pokemon_red/items.yaml (unknown ids
  self-tag as ITEM_0xXX for checkpoint harvest, same pattern as tiles).
  (2) REPETITION COUNTERS: per-map visit counts injected at >=3 ("[you
  have entered this map N times...]") — a 31B model uses an explicit
  counter far better than it infers recurrence from a 20-item recent list.
- **Stale notes don't fix themselves — force the rewrite at the decoder**:
  the model happily acts for rooms on notes it wrote in another building
  ("healed at the Center" written inside a random house). Asking nicely in
  the prompt is optional-by-construction when "memory" is an optional
  schema field. → the loop tracks the map notes were written on + decisions
  since; when notes predate a map change or go 15 decisions unchanged
  (and not in battle), "memory" flips to schema-REQUIRED for that call and
  the prompt says why — the decoder cannot omit the rewrite. Structured
  output as enforcement, not suggestion.


## Grounded context beats taught rules — the attestation suite (2026-07-20 late)

The evening's arc: every wedge traced to the model ACTING ON BELIEF where
the harness could have supplied truth. The fix each time was another
attested field in the {ram} view, not more prose rules. The suite as it
now stands (all HOT data, all live-verified or user-authorized):
- `place=` (maps.yaml) — three interior misidentifications (house-as-
  Center, house-as-Mart, lab-as-both) ended the day the map id got a name.
- `bag=` + "[bag: +/-N X]" events (items.yaml) — killed phantom-parcel
  beliefs; the model itself now cites "verified by the bag event".
- `party=` (species.yaml) — nick/species/level/HP/status + (LOW!); heal
  decisions need visible HP, not remembered battle outcomes.
- `bearings=` (run waypoints.yaml) — compass directions in goal text rot
  as the player moves (wrote "Mart is east", model walked west, then the
  text was wrong); live-computed bearings cannot rot. Map-edge gaps
  (connections, not warps) each need a waypoint until connection headers
  are read (run-2 item).
- `battle_hint=` (types.yaml + species types) — full Gen 1 type math per
  battle, both directions, worded verdicts. User authorized BULK game
  knowledge here (internal ids fetched from pret/pokered, chart with Gen 1
  quirks: BUG<->POISON 2x, GHOST 0x vs PSYCHIC, ICE neutral vs FIRE).
- Repetition counters ("entered this map N times") because a 20-item
  recent list can't show recurrence to the model.
Navigation macro completions from the same arc: counted walks
(walk_south_3 pairs with bearings), walk_to_exit goes THROUGH doors
(edge-press + off-screen approach + standing-on-mat), directional walks
fall back to ONE direct step when BFS has no goal (crosses map-edge
connections; the fix that finally made town boundaries walkable).
mash_through_dialogue final form: ALWAYS at least one A (user rule -
text-state flags keep having per-mode blind spots, wFontLoaded is
overworld-only), gated follow-through, never presses into a visible
choice cursor. Ops: goals_complete alarm fires on the LAST-numbered goal
stamped (instruction-style middle goals never stamp); checkpoint protocol
= strategy subagents with full context packages + self-initiated session
rotation.

## The skills thesis, tested live — wire POSITIONING, not conversations
## (2026-07-21 overnight, Viridian→Forest stretch)

- **The nurse yes/no exposed the real bug: plans don't stop at choices.**
  advance_text correctly stopped at the YES/NO cursor ("answer it with ONE
  deliberate press") — and then the plan runner executed the REST of the
  plan anyway; a queued walk's arrow presses moved the cursor onto NO and
  the next A silently CANCELLED the heal, repeatedly (HP pinned at 10/24
  across four attempts). The 0xED choice-cursor detection itself is now
  live-verified — it stopped exactly where it should; the wiring after the
  stop was the hole. → loop.py: a choice-stop aborts the remaining plan
  UNLESS the very next step is press_A/press_B — that one press runs and is
  shielded from the phash abort (the menu popping IS the expected change).
- **Full conversation skills work but were retired BY DESIGN**: scripted
  heal_at_center and buy_N_X skills each succeeded live (heal verified,
  bag +3 POKE BALL verified) — and were then deleted per user direction:
  wire positioning only, keep conversations as deliberate model presses
  under the choice-stop guard. Rationale: scripted menu walks are brittle
  world-state assumptions (exact stock order, exact prompt sequence) that
  fail opaquely; positioning is geometry the harness provably owns. The
  model handled the Antidote purchase manually right after — the guard +
  numbered UI drills in goals were enough.
- **walk_to_counter needs no per-map data at all**: the game's own tileset
  headers define counter tiles (talk-across mechanic), so the macro
  pattern-searches [person][counter tile][open space] in a straight line,
  walks to the space, face-taps the person. Works for every Center/Mart/
  gym desk in the game. Fallbacks: person off-screen → walk a few blocks
  north (Gen 1 interiors keep counters at the top) and re-search next call.
- **The warp table LIES about enterability** — the forest south gate lists
  exit mats at (4,0) AND (5,0), but (4,0)'s tile is wall 0x4a (door only
  at x=5). Force-opening warp blocks for BFS made the deterministic
  shortest path press UP into that wall forever (second gate wedge of the
  night). → navigate.py routes walk_to_* against a goal SET via
  multi-source BFS distance field + STOCHASTIC DESCENT (random pick among
  closer-or-level neighbors, never the block just left): a grid lie costs
  a couple of re-rolled decisions, not a wedge. Sim from the wedge tile:
  52% old route, 48% the working east-then-north.
- **Movement heuristics must be battle-gated.** The new walk-effectiveness
  watchdog (3 consecutive walks with zero position change → nav_ineffective
  escalation carrying N/S/E/W neighbor block ids) first fired mid-Kakuna
  fight: battle-menu DOWN presses look like movement attempts and position
  is frozen by design; the 0x7f-everywhere neighbor dump was the tell
  (battle screen over the tilemap). → gated on in_battle==0. The evidence
  payload is the point: neighbor ids diagnosed the gate wedge by hand
  before the watchdog existed; now they arrive in the escalation.
- **Read state SETTLED, not mid-warp**: map_id and pos are read at
  different instants during warp animations — logged torn pairs ("Pokemon
  Center" with street coords). → _tick re-reads every 0.5s until map/pos
  agree across two reads, THEN captures the frame, so place=, bearings and
  the screenshot describe one settled world (user: "0.5s delay for
  looping" — cadence stays 30s).
- **Authoritative ingest beats harvest for TABLES; harvest stays for
  BEHAVIOR.** Convention amended across the night (user-driven): map names
  (226), item names (95 + TM/HM), move names (165), per-tileset collision
  walkable lists, counter tiles, grass tiles — all pre-ingested from
  pret/pokered, because an unnamed/unmapped id is a wedge waiting to
  happen (the gate tileset proved it: unharvested = every walk macro dead;
  now also mitigated by a one-direct-press fallback + "[area not mapped]"
  feedback). Live verification is reserved for BEHAVIORAL claims — ledges
  (the 0x55 "ledge" that was a fence), anything one-way or conditional.
  Unused/placeholder ids are omitted on purpose: an ITEM_0xXX or
  "map N (unknown)" tag now signals a REAL gap, not missing homework.
- **party= carries the move list + PP in MENU ORDER** ("1 SCRATCH (31 PP),
  2 GROWL (38 PP), 3 EMBER (23 PP)") — the slot number IS the DOWN-press
  count, and PP exhaustion is visible instead of remembered ("UNUSABLE!"
  at 0). Battle move selection stopped being a memory task. → PartyConfig
  moves_off/pp_off (PP byte masked 0x3F, top bits are PP-Ups), HOT
  data/pokemon_red/moves.yaml.
- **walk_to_grass walks INTO the grass and paces**: encounters roll per
  step THROUGH grass, so stopping at the border was worth one roll; the
  route extends with a random grass-only stroll to the step cap, and the
  harness remembers where grass was last seen per map (heads toward it
  when none is on screen; honest "[no grass in sight on this map]" when
  never seen). Grass renders as `"` on the map from the tileset-header
  grass ids.
- **Ops**: current-goal viewer (tools/goals_server.py, :8702) serves the
  first un-[DONE] goal for OBS/browser — standalone so harness restarts
  don't kill it. done_goal is now confirmed BOTH too eager (false Center
  heal) and too lazy (skipped the obvious forest-entry stamp) — the
  checkpoint stamps/prunes on evidence either way. And the launch-cwd
  gotcha bit again mid-incident: a backgrounded harness relaunch from the
  wrong cwd failed with "path not found"; the verify-every-step drill
  (harness_start + pids or it didn't happen) caught it in one cycle.

## Conflict economics, battle geometry, tripwire-judge, trajectory
## detectors (2026-07-21 day — limits-4 forest arc)

- **Prompt conflicts have a measured price, and "inapplicable" is a
  conflict too.** Same phase, same map: overworld decisions at <50% HP ran
  median 45.5s vs 30.9s healthy (+47%) — the model re-litigating "Potion
  early" against an empty bag every step; battles with EMBER at 0 PP ran
  41.7s vs 30.5s (+37%). The extreme tail was worse than slow: 187-190s
  "decisions" were fallback entries — deliberation ran past the reply
  format and broke it. Fixes, each worth its cost the same hour: prompt
  rule "the FIRST rule that fits wins; a rule you cannot follow right now
  does not apply - skip it without discussion"; goals get RULE-SILENCING
  lines when a stretch predictably disables a rule ("no POTIONs until
  Pewter - Potion rules do not apply on this walk"). Post-fix: median
  49.8→38.6, >90s events 7→1. → prompt.md Planning, goals convention.
- **A rule that can co-trigger with a goal drill needs an explicit yield
  clause.** Generic "Every fight: attack_3" vs goal-12 "flee or attack_1"
  cost a 53s think on the very first skill use even WITH the precedence
  rule in the prompt — precedence resolved it, but only after a full
  deliberation lap. Rewrite the rule to defer itself: "a fight the
  current goal does not say how to handle: ...". → goals Rules wording.
- **Battle menus are GEOMETRY, not conversation** — the boundary that
  retired heal_at_center leaves them wireable. Gen 1 remembers cursor
  position across turns (move menu restores to the LAST-USED move,
  pokered-verified), which is why the old manual drill "A, DOWN, DOWN"
  only ever worked while EMBER sat in the bottom slot of a 3-move list
  (no-wrap DOWNs pin the bottom). Skills attack_1..4/flee_battle do
  reset-to-corner then navigate: advance_text in (reach the menu without
  pressing into a cursor), B B collapse, UP LEFT pin FIGHT (both battle
  menus have NO wrap — extra presses are no-ops), exact arrows, confirm,
  advance_text out (play the turn to the next menu). One battle turn =
  ONE behavior. 6/6 escapes on day one. → skills/pokemon_red/*.yaml.
- **Prose multi-press drills execute as ONE press per decision.** The
  first flee fix taught "press DOWN then RIGHT then A" as goal text; the
  model issued single presses across separate decisions, drifted into the
  bag menu mid-sequence, and burned 5 decisions per Weedle. Sequences the
  harness can own must be WIRED (a skill), not taught (prose) — teaching
  belongs only to genuinely one-press answers. → the skills above.
- **Tripwire-judge step validation** (op verify; PLAN §2): the tripwire
  (a profile ram_map read, e.g. in_battle==0 after flee) decides only
  WHETHER to ask; the LLM judge on the settled screenshot rules
  {matches, seen} as sole authority. Predicted-outcome asserts are
  BANNED (harness world-model claims = the warp-table/0x55 class).
  Fails open, every verdict metered. First live data: both judge calls
  were false summons — in_battle LAGS the escape text, so the tripwire
  read 1 on already-won escapes → a 90-frame settle wait before the
  tripwire now answers most checks free. Watch item: both verdicts
  described the frame as "glitched overworld" (dense forest tiles vs a
  real capture problem — compare wording from open terrain). Portability
  ladder for future games: RAM tripwire → pixel/phash tripwire →
  always-ask floor; judge identical everywhere. → executor.py,
  policy/llm.py verify(), prompts/<game>/verify.md, flee_battle.yaml.
- **Bearing-chasing is a wedge class stuck detectors cannot see.** Two in
  one morning, ~2h each: (1) a GHOST ITEM — the collected forest ball
  kept advertising because object tables aren't filtered by the missable
  flag, luring the model back into a dead-end pocket; (2) COMPASS-VS-MAZE
  — "forest exit corner: 31 north" crosses tree walls; BFS's ~12-tile
  horizon can't discover a detour that starts 20 tiles east, so
  walk_north re-rolled the same 7-tile lap for hours. Positions kept
  CHANGING, so position-stuck/phash detectors stayed silent (the naming-
  grid blind spot again, movement flavor). And the "obvious" fix made a
  THIRD wedge: routing the model to the Potion first — its alcove opens
  from the far side; an item bearing 3 tiles away can be unreachable.
  Fixes: ordered route-leg waypoints in natural language ("the path
  north (east side)" → "the top corridor" → "the west lane"), goals text
  "the forest is a MAZE - do not chase the exit bearing directly", and
  items on a route are opportunistic pickups ("only if 1-2 tiles away
  while ON the path"), never first-class stops. Backlog: filter
  collected items from bearings; pathability-aware bearing rendering.
  → run waypoints.yaml/goals.md pattern; harness backlog.
- **The model cannot see its own trajectory — the harness must hand it
  over** (user design). Confusion detectors in the loop: loop_detected
  (16 recent overworld moves cover ≤9 distinct tiles, any tile revisited
  4+, mostly walks, one map) and slow_streak (3 consecutive decisions
  over max(60s, 3× rolling median) — self-calibrating, no fixed
  constant). Ladder: rung 1 injects the evidence into the NEXT decision
  via the stale_notes pattern ("16 moves cover only 6 tiles; (6,30)
  visited 4 times. Walking there again will fail again. Do something
  DIFFERENT") — self-diagnosis is impossible from inside one locally-
  reasonable decision, trivial when the trajectory is in the prompt;
  rung 2 escalates with the evidence payload if it persists 10+
  decisions; 8 quiet decisions re-arm. Both fires metered for threshold
  tuning. Deferred rung 0: adaptive thinking cap — only rung that can
  hurt. → loop.py _watch_confusion/_ladder, llm.py intervention.
- **Ops: Bash-tool background launches can die cleanly ~35s in** (console
  control event → the loop's KeyboardInterrupt path; banner + one
  decision logged, exit 0, no traceback — looked exactly like a code
  bug). Foreground `timeout N` diagnostics lose buffered metrics on the
  kill (missing harness_start ≠ never started). The reliable launch is
  fully DETACHED: Start-Process cmd /c with -WorkingDirectory, then the
  drill (pids + harness_start + a fresh decision + survive >60s).
  Session-scoped cron proved unreliable under a busy session (a :07
  hourly never fired in 90 min); watchers + explicit checks carried the
  duty. → harness-machine-ops memory.

## Sentences beat structure, intents beat inputs, data beats prose
## (2026-07-21 afternoon — limits-4 Pewter arc)

- **No technical jargon anywhere the model reads** (user rule). Profile
  `state_lines` renders every state field as a sentence ("You are NOT in
  a battle." / "You are carrying ¥2335."); map_id/party_count hidden as
  redundant. prompt.md re-anchored from field names to the sentence
  vocabulary. Then the ASCII map grid was REMOVED entirely (user
  thesis): bearings + stride opening reports + edge lines + can_move +
  last_move carry everything the grid did — the model never read the
  grid well anyway (one-block gaps invisible), and durations dropped
  when it left. → profiles state_lines, prompt.md, commits 0ece838,
  5baa6db, dbdba38, d7eff37.
- **Navigation goals must be micro-goals**: one tangible action, one
  DONE line in state vocabulary, stamped one at a time (user directive
  after the maze prose overwhelmed the model). Verifiable DONE lines
  cut false done_goal stamps but did not END them — three false stamps
  in one day ("Leave the forest" while in it; BOULDERBADGE at badges=0
  twice-removed). goals_complete is NOT evidence; the checkpoint
  verifies RAM before acting on it. done_goal grounding guard is the
  top harness item for run-2. And PRUNE stamped goals to one-line stubs
  IMMEDIATELY: 40 lines of dead forest instructions correlated with
  llm_failure spikes and 190s decisions in Pewter.
- **The intent vocabulary generalized** (user: hardcoded skills are
  cheating): use_<item>/buy_<item>_x<n> minted per decision from bag +
  mart tables (closed enum — the model cannot name what is not there),
  slots/counts resolved to cursor math at execution; walk_to_<landmark>
  minted per same-map waypoint (BFS with a local-optimum stop that
  SAYS "as close as the ground allows"). Skills CHECKPOINT their
  screen through the judge (user escalation): verify+abort_on_fail at
  every transition, the judge's seen-text as feedback — the shop focus
  trap (BUY/SELL/QUIT keeps focus while the item list renders) cost 40
  blind minutes before checkpoints existed. Quantity boxes need a
  render wait before counting (x5 asked, x1 bought). Total shopping
  tuition: ¥2400 → ¥25, 3 stray Poke Balls, one hour.
- **Probe tiles after two failed prose fixes.** The Pewter gym door ate
  3 hours of theories (poles east! opens west! enter from the mart
  street!) — every one wrong. A per-tile walkability dump over a second
  bridge connection settled it in minutes: the yard pocket is fenced
  east by a 0x55 tile (the fence id AGAIN), walled south, and opens
  only from the far west. Screenshots and the block-grid render are
  ambiguous at 2x2; the ONLY trustworthy view is per-tile ids at
  explicit map coords (scratchpad probe_area.py pattern). Corollary:
  outdoor door entry is an intent skill problem (enter_<building>),
  never prose — doors sit outside the walkable set, so counted walks
  and strides stop BESIDE them and only a raw press enters.
- **Ops**: raising max_tokens 4000→6000 traded budget failures for
  240s timeouts — the timeout ceiling and the thinking cap must move
  together (rung-0 adaptive cap now has its dataset). Transient NPC
  blocks need distinct phrasing from walls in can_move (the model
  reroutes around people instead of waiting). nav_ineffective and the
  confusion detectors all need a menu/dialog gate (five menu false
  positives in a day). walk_to_exit outdoors walked INTO the nearest
  building (five accidental re-entries) — resolved 2026-07-22 by
  REMOVING the behavior (next section).

## Cleanup and the quest feed (2026-07-22 evening — user directives)

- **The quest tree moved INTO the harness** (revising the morning's
  checkpoint-side-only call): prompts/<game>/quests.yaml is a
  structured tree — acts (verbatim player titles, verify anchors,
  per-act rules) holding quests (text, DONE line, budget_min, status).
  harness/quests.py feeds it piecemeal (act ladder with done-collapse
  and YOU ARE HERE, exactly one current quest), runs the budget clock,
  and records the model's marks: done_goal -> status done +
  goal_stamped/act_stamped escalations; a COACH note -> status coach.
  Glue-consistent because the harness only turns pages: every word is
  checkpoint-authored and every stamp is checkpoint-validated. The
  derivation contract that was prose convention is now code — the
  rendering cannot drift from it. goals.md remains the fallback for
  runs without a quests.yaml.
- **Vocabulary pruning rule: a behavior that needs usage bans is a
  removal candidate.** walk_to_exit carried two standing bans (walks
  INTO buildings outdoors; picks the near door in gates) and still
  wedged runs — REMOVED, with its navigate.py special cases. Rooms
  are left by walking onto the doormat (can_move announces doorways)
  plus one edge press; doors are entered by one press. enter_door_above
  (built for one Pewter doormat) — REMOVED; it was a skill-shaped
  patch for a routing problem. Keep: attack_1..4/flee_battle (every
  battle in the game), walk_to_counter/walk_to_grass (every town/
  grind), minted use_/buy_/walk_to_ intents (closed-grammar, data-
  driven).
- **Fetch, don't recall.** Mart inventories and map-name gaps written
  from memory in the first master-plan draft were replaced by fetching
  pret directly: marts.asm gave the whole-game shop table in one pull
  (the recalled Lavender list had dropped ICE HEAL; menu order drifted
  elsewhere), and map_constants.asm exposed ~40 reachable maps
  missing from maps.yaml (all Silph floors, all Safari areas, Rock
  Tunnel B1F, the mansion basement, every Elite Four room) — each one
  a guaranteed "map N (unknown)" wedge the run would have hit at the
  worst time. The hour of fetching beats any amount of confident
  recall; recall is only for choosing WHAT to fetch.
- **State serving stays generic.** The proposed safari-steps field
  (zone-specific countdown) was cut: a field that serves one room of
  one game is the pattern the serving criterion exists to block —
  quest text carries zone quirks instead ("the game ends itself and
  returns you to the gate"). Owned-kinds and a surfing line remain
  the only planned additions (game-wide, DONE-line-checkable).
