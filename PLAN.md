# llm-plays — Plan

An autonomous game-playing system: a local LLM makes moment-to-moment decisions, a
deterministic harness guarantees the system never stalls, and Claude performs periodic
checkpoints to summarize progress, unstick the agent, and grow a reusable skill library.

Target arc: emulated Pokémon Gen 1 → all Pokémon generations → real console hardware
(Switch) → progressively less forgiving games.

---

## 1. Thesis and invariants

**Original thesis:** for forgiving games ("a fish can beat it"), an agent wins as long as
it never stops inputting. **Generalized thesis** (so the harness survives harder games):

> The harness always has *some* policy to execute, always knows how much it trusts it,
> and never allows unrecoverable loss of progress.

Three hard invariants, enforced by the harness (never delegated to any LLM):

- **I1 — Liveness via fallback ladder.** A watchdog guarantees a valid action is always
  produced. Fallback rungs, per game profile:
  1. Local LLM decision (normal operation)
  2. Scripted behavior from the skill library
  3. Safe idle (pause / stand still / block — the do-no-harm floor)
  4. Random input ("fish mode") — enabled only where the game profile permits
- **I2 — Progress ratchet.** The harness enforces save discipline ("never more than
  N minutes from a save/savestate") as a scheduled injected behavior. Failure then costs
  bounded time, converting punishing games back into brute-forceable segments.
- **I3 — Bounded stuckness.** Stuckness is detected mechanically by independent
  signals (screen-novelty stagnation, position pinned with no RAM progress,
  behavior loops, milestone drought — harness/stuckness.py), and the response is
  staged: one bounded random-input self-rescue first, then escalation rather than
  waiting for the next scheduled checkpoint.

**THE CORE PRINCIPLES (user, 2026-07-22 — the frame everything else
elaborates):**

1. **The checkpoint THINKS, the local LLM ACTS, the harness BRIDGES the
   gap between them.** Strategy, plans, validation, and hard calls are
   checkpoint work; every in-game choice is the local LLM's; the harness
   is the bridge and nothing more — it never thinks and it never acts on
   its own judgment.
2. **The local LLM is limited but a bit smart — the checkpoint breaks
   tasks down FOR it.** Never hand it a plan it must decompose itself:
   hand it one small quest with a checkable DONE line, sized so that
   "a bit smart" is enough. When it struggles, the fix is a smaller or
   clearer task, not a smarter harness.
3. **Communication with the local LLM is NATURAL LANGUAGE, only.** The
   harness may read RAM, grids, and tables, but everything it conveys is
   plain-language sentences a player could say ("You are in Pewter City.
   From this tile you can step: south, east." / "x = 12"). No raw field
   names, no data structures, no engine jargon — if it cannot be said
   plainly, it is not ready to be served. Coordinates ARE plain language
   (user 2026-07-22): human players follow walkthrough coordinates too;
   the forest lesson was about GUESSED coordinates being wrong, so
   verify them — then use them freely in state lines and quest text.

**The harness is GLUE (the same statement, mechanism-side).**
Three parties: the LOCAL LLM plays the game; the CHECKPOINT (Claude) plans
the strategy; the HARNESS glues them — it (a) provides useful information
the player cannot infer for itself, (b) provides the mechanisms that
convey intent: the model's intents down into the game (skills, walks,
menu geometry), the model's claims and flags up to the checkpoint
(stamps, COACH flags, alarms), and the checkpoint's strategy down to the
model (goals presentation). The harness never plans, never judges, never
tracks strategy state.

Goals-presentation revision (user, 2026-07-22 evening): the quest tree
now lives at prompts/<game>/quests.yaml and the HARNESS ingests it —
feeds one quest at a time under the act ladder, runs the time-budget
clock, records the model's done/coach marks, and escalates every stamp
(goal_stamped / act_stamped, with the checkpoint's own verify anchors
echoed back). This is presentation MECHANICS, not planning: the
checkpoint authors every word (titles, quest texts, DONE lines, budgets,
rules, verifies) and remains the sole validator of stamps; the harness
merely turns pages. The earlier rejections stand for what they were —
a route tracker that computed the model's plan-position (the model's
cognition) and a tree walker that would have chosen strategy; a
mechanical page-turner over a checkpoint-authored file is neither.

**Navigation division of labor (decided 2026-07-21, after the limits-4
forest arc).** Constraint set by the user: the local LLM is not very smart,
everything it reads is natural language, and the harness must not direct or
judge. So navigation splits three ways:

- **Harness: facts only, as sentences.** What is here ("You are in X", the
  battle/team/bag lines), what is adjacent ("From this tile you can step:
  south, east. You cannot step: north (an obstacle)"), what just happened
  ("Your last movement: walking north you went 9 tile(s); openings passed:
  east after 3"), where the world ends ("You are ON the northern edge"),
  and — run-2 — what the model itself has already covered ("the top-left
  pocket is fully explored - a dead end", "unexplored ground lies south",
  "your last 6 walks net moved you 2 tiles"). Facts about the world or the
  model's own history; never "go this way", never a verdict. The ASCII map
  grid is gone from the prompt — the local LLM could not read it (one-block
  gaps invisible), and the sentence set replaced it with no loss.
- **Checkpoint: strategy in natural language, validated against data.**
  Routes are micro-goals — one tangible action each, an explicit verifiable
  DONE line in the state vocabulary ("DONE when your location reads Route
  2: mark it done then") — and procedures over coordinates ("take the FIRST
  opening WEST a walk report shows"): two coordinate guesses were falsified
  live in one forest; the procedure fixed both. Complex approaches get
  ordered CARDINAL SUB-STEPS inside the goal, each anchored to a landmark
  bearing ("(a) WEST until X reads 2 or less; (b) NORTH until Y; (c) EAST
  along the row - never step south, that is the ledge") — decided
  2026-07-22 over the alternative of a wired move-to-<place> macro, which
  the user rejected as cheating: the model must still walk the route; the
  checkpoint provides the legs and the landmarks, never the walking.
  Each sub-step carries its own CHECK — a condition the model validates
  itself against its state lines — and the model keeps the progress
  record in its NOTES, fixing them when the screen disagrees (user, same
  day: a harness-side sub-step tracker was built and REVERTED — knowing
  which stage of a plan you are in is the model's cognition, validated
  by it, not computed for it; the harness contributes facts, the goals
  contribute checkable conditions). The goals file opens with a GOAL
  TREE (user 2026-07-22): the road to beating the game, decomposed —
  Elite Four ← 8 badges ← the current badge's sequence, with YOU ARE
  HERE marked. Every decision sees why the current goal matters, goal
  validation gets an anchor (a goal is sensible relative to its
  parent), and the model is told to report impossible/already-true
  goals in its notes instead of forcing a stamp — the checkpoint reads
  notes and rewrites the plan. Run-2: ingest pret
  walkability grids so waypoint anchors are validated (unwalkable -> snap
  to nearest walkable) instead of guessed, and map-connection headers so
  edge crossings are announced as facts the game itself shows.
- **Model: every choice.** The drills it follows live in goals text it can
  quote; the harness executes geometry it could never sequence (strides,
  battle menus) but picks nothing.

## 2. Architecture

```
                       ┌──────────────────────────────────────────┐
                       │                HARNESS (Python)          │
   ┌────────┐  frames  │  ┌─────────┐   ┌──────────┐  behaviors   │  ┌───────────────┐
   │  EYES  ├─────────►│  │ CV      │   │ Decision │─────────────►│  │   EXECUTOR    │
   │ driver │          │  │ sidecar │──►│ loop     │              │  │ (frame-rate,  │
   └────────┘          │  └─────────┘   └────┬─────┘              │  │  reflexes)    │
                       │                     │ watchdog /         │  └──────┬────────┘
                       │                     │ fallback ladder    │         │ inputs
                       │  ┌──────────────────┴───────────┐        │  ┌──────▼────────┐
                       │  │ state files, logs, metrics,  │        │  │    HANDS      │
                       │  │ escalation queue             │        │  │    driver     │
                       │  └───┬──────────────────▲───────┘        │  └───────────────┘
                       └──────┼──────────────────┼────────────────┘
                       decide │                  │ read/write
                     ┌────────▼───┐      ┌───────┴────────────────┐
                     │ LOCAL LLM  │      │ CLAUDE CHECKPOINT      │
                     │ (Gemma,    │      │ (scheduled + escalation│
                     │  JSON-     │      │  -triggered; via MCP)  │
                     │  constrained)     │ summarize, update goals│
                     └────────────┘      │ author new skills      │
                                         └────────────────────────┘
```

**Division of labor by timescale:**

| Layer          | Cadence      | Who                | Job                                        |
|----------------|--------------|--------------------|--------------------------------------------|
| Reflex         | per frame    | Executor (code/CV) | run behaviors, scripted reactions          |
| Decision       | 1–5 s        | Local LLM          | pick next behavior from skill library      |
| Strategy       | 5 h / event  | Claude checkpoint  | summarize, unstick, update goals, write skills |

The local LLM is a *behavior selector*, not a button presser. In Phase 1–2 the "skill
library" is nearly empty (behaviors like `press_A`), but the interface exists from day one.

**Step validation — tripwire-judge (decided 2026-07-21).** Skills may carry
`op: verify` steps ({expect, tripwire}). The tripwire — a cheap engine-bit
read against the profile ram_map, e.g. `in_battle == 0` after flee — decides
only WHETHER to ask; it never rules on truth (predicted-outcome asserts are
banned: harness world-model claims are exactly what the warp-table/0x55
lessons burned). When the tripwire is absent, unreadable, or tripped, the
JUDGE rules: the local LLM gets the settled screenshot and one line of
expectation (template `prompts/<game>/verify.md`, checkpoint-owned, hot) and
returns `{matches, seen}` — the sole authority on what happened. Fails open
with loud feedback; every verdict logged (`kind: "verify"`) so the judge's
own accuracy is auditable. Portability ladder for future games: RAM tripwire
where mapped → pixel/phash tripwire where not → always-ask as the floor; the
judge layer is identical everywhere. Rationale: the model keeps decision
authority (user), the common success path costs zero LLM calls, and every
anomaly gets model eyes. Pilot: flee_battle escape confirmation; next:
done_goal grounding. Escalated 2026-07-21 (user, after the shop focus
trap): skills CHECKPOINT their screen through the judge - a verify step
with abort_on_fail at entry and after every screen transition, so a
sequence never fires into a screen it has not confirmed; on mismatch the
skill stops and the judge's seen-text goes to the model as feedback
("[buy_potion_x5 stopped - expected the shop's item list; the screen
shows: ...]"), turning a blind misfire into an informed next decision.

**Intent vocabulary (sharpened 2026-07-21, user directive).** The model's
allowed-behaviors list is a vocabulary of INTENTS, not inputs: the harness
executes what the model means; the model never hand-drives geometry. The
boundary test: anything whose button sequence is deterministic once the
intent is known (menus, shops, item use, battle turns) gets wired as a
skill the moment its geometry is understood; raw single presses remain
only for genuinely one-press answers (a yes/no the model must read) and
novel screens. Evidence: curing one poison via raw presses cost 8
decisions and a Pokedex detour; the same intent is one `use_antidote`
call. Conversations stay with the model (knowledge boundary) but a skill
may CARRY one (a buy holds the clerk dialogue) when every answer is fixed
by the intent itself. Generalized same day (user: hardcoding the answer
in a skill name is cheating — the checkpoint pre-deciding what to buy):
`use_<item>` / `buy_<item>_x<n>` are name-encoded arguments (the
counted-walk pattern) resolved by harness/items.py at execution — names
are MINTED per decision from the bag and the current map's shop table
(data/<game>/marts.yaml, pret-sourced), so the grammar enum stays closed
and the model can never name an item that is not actually there; slots
and counts become cursor math at runtime. The model supplies item, count,
and moment; the harness supplies fingers.

## 3. Interfaces (the seams that make platform/game swaps config, not rewrites)

```python
class Eyes(Protocol):
    def get_frame(self) -> Frame                  # emulator screenshot | OpenCV capture

class Hands(Protocol):
    def press(self, button: str, hold_ms: int)    # emulator API | serial→Pico | 3DS InputRedirection
    def hard_reset(self)                          # recovery path; required on console

class Extras(Protocol):                           # nullable — console returns Unsupported
    def read_ram(self, addr_map: dict) -> dict    # badges, map id, party state, ...
    def savestate(self, slot: int); def loadstate(self, slot: int)

class Executor:
    def execute(self, behavior: Behavior)         # runs a skill at frame rate; interruptible

class LocalPolicy(Protocol):
    def decide(self, obs: Observation) -> Behavior  # JSON grammar-constrained output
```

**Drivers planned:** mGBA (Lua/scripting socket) → melonDS/Citra → capture card
(OpenCV) + Pico controller board (serial) for Switch.

## 4. State on disk (per game run)

```
runs/<game>/<run-id>/
  quests.yaml         # the quest tree, seeded from prompts/<game>/quests.yaml:
                      #   checkpoint-authored acts/quests with DONE lines and
                      #   time budgets; harness feeds one quest at a time and
                      #   records done/coach marks; supersedes goals.md when present
  goals.md            # legacy strategy prompt; rewritten by Claude, injected into local-LLM prompt
  memory.md           # the local model's SELF-maintained notes (location, task) — written
                      #   via the "memory" field of its replies, carried verbatim into the
                      #   {memory} placeholder; checkpoints correct false beliefs
  progress.md         # rolling summary maintained by Claude checkpoints
  briefing.md         # harness-computed checkpoint digest (totals, milestones, open
                      #   escalations, current notes/goals) — regenerated on escalation
                      #   and via `python -m harness.briefing <run-dir>`; Claude reads
                      #   this FIRST instead of parsing raw JSONL
  log.jsonl           # structured: ts, obs hash, chosen behavior, rung, result
  metrics.jsonl       # progress signals: frame-hash churn, RAM milestones, deaths, saves
  escalations.jsonl   # stuck-flags and help requests; consumed by Claude
  snapshots/          # periodic screenshots + savestates
profiles/<game>.yaml  # HARNESS config (see below) — COLD: editing it means tearing down
                      #   the harness and starting a new run segment; each run stores a
                      #   snapshot of the profile it ran under (results stay attributable)
prompts/<game>/       # GEMMA-facing: prompt.md (THE per-decision prompt, read fresh from
                      #   disk every LLM call — placeholders {behaviors} {goals} {ram}
                      #   {recent} {max_plan} filled by the harness) + goals.md (run seed)
                      #   — HOT: checkpoints rewrite these mid-run; live next decision.
                      #   Validated per read (required placeholders, 8k size cap); a bad
                      #   edit falls back to the last good version + escalates. Each
                      #   game's prompt.md is self-contained BY DESIGN (duplication
                      #   accepted): harness-contract changes require migrating every
                      #   game's prompt file. Decisions log a prompt hash for
                      #   per-version attribution.
prompts/claude_checkpoint.md  # the checkpoint job description
skills/<game>/        # behavior library: scripted macros, grows over time (Claude-authored)
skills/common/        # cross-game behaviors (mash dialogue, menu nav patterns)
```

**Game profile** (`profiles/<game>.yaml`) declares: button map, fallback ladder config
(is random allowed? what is safe-idle?), save-ratchet interval, escalation thresholds,
RAM address map (if emulated), decision cadence, prompt template.

**Write paths — no LLM edits files freely:**
- *Gemma* cannot touch files at all: it emits structured JSON fields and the HARNESS
  applies them (today: the `memory` field → memory.md). Extending Gemma's write powers
  means adding a schema field + a harness apply-step, never file access.
- *Claude* edits files with its own tools at checkpoint time (Claude Code on this
  machine; the MCP server adds game powers, not file powers) — but every edit is
  validated where the harness CONSUMES it, so a bad write degrades, never stalls:
  invalid prompt.md → last-good version + `prompt_invalid` escalation; malformed
  skill YAML → skipped + `skills_invalid` escalation; goals/memory are plain text
  read fresh each tick (worst case: bad advice, still bounded by the ladder).

## 5. Claude checkpoint

- **Trigger:** scheduled every ~5 h (usage-reset aligned) **or** early-woken by an
  escalation event, whichever comes first.
- **Access:** an MCP server exposing `tail_log`, `get_metrics`, `screenshot`,
  `read_ram`, `press_button`, `save/loadstate`, `read/write goals.md`,
  `add_skill`, `resolve_escalation`.
- **Duties, in order:**
  1. Triage escalations — diagnose stuckness from snapshots/log; if softlocked, use
     loadstate (emulator) or direct recovery play (console).
  2. Compress `log.jsonl` into `progress.md`; prune consumed logs.
  3. Rewrite `goals.md` — next objectives, warnings ("stop re-entering that cave").
  4. Author skills — turn observed failure patterns or puzzle solutions into scripted
     behaviors the local LLM can invoke thereafter. **The skill library is the
     compounding asset across the whole project.**

## 6. Calibration mode & benchmarks

On any new game: run rung-4 (pure fish) for 30–60 min, log metrics. Output: is this game
fish-beatable, how tight must the save ratchet be, escalation thresholds. Also establishes
the baseline the LLM must beat — keep this graph.

The project's headline output is comparative: hours-to-champion vs the fish (3,195 h),
Twitch Plays Pokémon (391 h), and the frontier-LLM-per-step runs (Gemini 2.5 Pro: 813 h).
Baselines, measurement rules, and the three-arm attribution design (fish / local-only /
full system, one shared harness) live in **BENCHMARKS.md**. RAM-change milestones in
`metrics.jsonl` are the raw material for the progress curves.

## 7. Roadmap

**Phase 0 — Environment.** mGBA with scripting enabled; Python env; local LLM server
validated per §7.1 (user supplies game ROM/cartridge dumps they own).
*Exit: can screenshot + press a button from Python; §7.1 checklist passes.*

### 7.0 Latency strategy (the local model is smart enough but slow)

Expected: 3–6 s per vision decision on the B70 (Gemma-3-27B Q4). Levers, by priority:
1. **Plan, not action** (✅ implemented): one LLM call returns a plan of up to
   `max_plan_len` behaviors (raw key presses included); the loop executes it at
   frame rate and cancels remaining steps when the inter-step frame-hash change
   exceeds `plan_abort_pct` (wild encounter, dialogue popup). Cuts call
   frequency 5–10×. Tune both knobs per game profile.
2. **Event-driven decisions** (Phase 2): consult the LLM only when the plan exhausts
   or the screen changes meaningfully — never on a fixed timer during animations.
3. **Speculative decisions** (Phase 2/4): infer during execution of the previous
   behavior; apply only if the frame is still similar, else discard and re-ask.
4. **Cheaper calls**: try Gemma 12B before 27B (measure vs fish baseline, don't
   assume); byte-identical static prompt prefix for vLLM prefix caching; cap the
   `why` field (~15 words); verify guided-JSON isn't on a slow path.
5. **Skills as a latency cache** (Phase 4): every Claude-authored skill and CV
   pre-filter turns future LLM calls into frame-rate scripts. Track `% rung-1
   decisions` over time — it should fall.

Anti-recommendations: no second GPU (open multi-Arc vision/TP bugs); no panic-drop
to ~4B models before measuring — "smart but slow" beats "fast but stuck".

### 7.1 Local inference server (Intel Arc Pro B70)

Planned hardware: Intel Arc Pro B70 (32 GB GDDR6, 608 GB/s, Battlemage). Sized right for
Gemma-3-27B-class VLMs at Q4 with KV headroom.

**Decision: Ubuntu 26.04 LTS + Docker + Intel LLM-Scaler vLLM container** (official Arc
Pro B70 support, INT4/FP8 online quant; the oneAPI userspace stays inside Intel's
container, host only needs the in-kernel Xe driver). Fallbacks, in order: IPEX-LLM
Ollama on 24.04 (currently broken on 26.04 — missing oneAPI runner), llama.cpp Vulkan
(zero-setup break-glass; strongest grammar constraints). Single GPU only until the
open multi-Arc vision-crash and dual-B70 TP bugs are fixed. Intel AI Playground is used
only to smoke-test the card — the harness requires a headless OpenAI-compatible API.
Full steps: INSTALL.md.

Validation checklist — **run 2026-07-20 against the live box** (Gemma-4-31B-it-QAT
w4a16-ct on `intel/llm-scaler-vllm:0.21.0-b1`, single B70, server 192.168.1.30:8000):
- [x] Vision model served; text generation on-GPU confirmed. (Plan evolved: Gemma 4
      31B QAT compressed-tensors, loaded natively — `XPUwNa16LinearKernel`.)
- [x] **Vision request works** (synthetic GB frame correctly described), single card.
- [x] **Constrained JSON output enforced** (vLLM json_schema guided decoding; the
      harness's actual plan schema validated end-to-end).
- [x] **Latency measured: ~1.1 s per vision+JSON decision** (steady-state; 20-23
      completion tokens). 3-5× better than the 3-6 s planning estimate — plan-of-8
      amortizes to ~0.14 s/action. decision_cadence_s set to 2.0 in the profile.
- [ ] Degradation path (OpenVINO OCR/CV → text-only prompt) — deferred; vision works
      well enough that this drops to a Phase 4 nice-to-have.

Container gotchas found during bring-up (for future rebuilds): the image bakes in
Intel's corporate proxy (`http_proxy=proxy.iil.intel.com:911` — override with empty
`-e http_proxy=`); `--group-add render` must use the numeric GID; use bridged
networking + explicit `--dns`, not `--net=host`. See `serve_gemma.sh` on the box.

**Phase 1 — Harness skeleton (no LLM).** Eyes/Hands drivers for mGBA, executor with
trivial behaviors, watchdog, fish mode, structured logging, snapshots. *Exit: fish plays
Pokémon Red unattended overnight — starting cold from the title screen (no primed
save-state assumption; boot is just another screen), and logs/snapshots are reviewable
next morning.* The no-primed-game rule is general: power-on, hard-reset recovery, and
first boot all land on title/menu screens, covered by prompt.md grammar + goals
objective 0 + the boot_mash skill.

**Phase 2 — Local LLM in the loop.** Observation builder (frame + goals.md + recent
context), grammar-constrained decisions, full fallback ladder, game profile loading.
*Exit: local LLM demonstrably outperforms the fish baseline on progress metrics.*

**Phase 3 — Claude checkpoint.** MCP server over harness state; scheduled checkpoint;
escalation queue + early-wake; progress.md/goals.md loop working. *Exit: a stuck run is
diagnosed and unstuck by a checkpoint without human help.*

**Phase 4 — Skills & hierarchy.** Real behavior library (menu nav, heal, save, shop);
CV sidecar (stuckness hashing, UI template matching); Claude authoring new skills at
checkpoint time. *Exit: Pokémon Red beaten end-to-end.*

**Phase 5 — Generation ladder.** Gen 2–5 via emulator drivers (mostly new profiles +
RAM maps, same harness). Calibration mode run per game. *Exit: multiple gens beaten;
porting a new game takes a profile, not code.*

**Phase 6 — Console rig.** Capture card Eyes driver; Pico/AVR Switch controller Hands
driver; Extras degrades gracefully (vision-only progress, in-game-save ratchet,
hard-reset recovery). *Exit: Gen 8/9 playing on real hardware.*

**Phase 7 — Balatro.** The anti-fish target: turn-based, zero reflex demands, but
random input never wins — the LLM must carry. First PC target: window-capture Eyes
driver + OS-level mouse/keyboard Hands driver; OCR reads score/ante/money (no RAM map).
Fixed seeds + stakes for reproducibility. *Exit: wins runs at a measured rate.*

**Phase 8 — Baldur's Gate 3.** The long-horizon boss: turn-based combat, real-time
exploration, deep quest state. Native saves = natural ratchet; Claude checkpoints do
quest-level planning and party builds. *Exit: main story completed autonomously —
or an honest writeup of where the ceiling is.*

## 8. Console-phase hardware (buy at Phase 6, not before)

- HDMI USB3 capture device (~$20–150)
- Raspberry Pi Pico flashed as wired Pro Controller (~$5) + serial link
- HDMI splitter (optional, to watch while it plays)

## 9. Risks / open questions

- **Local LLM vision quality** on Game Boy frames — may need upscaling/palette
  normalization, or leaning harder on RAM/OCR text extraction than raw vision.
- **Decision latency budget** — Gemma-class vision inference time sets the real cadence;
  measure in Phase 2 before tuning prompts.
- **mGBA scripting surface** — confirm socket/Lua API supports frame capture + input
  injection + savestates cleanly; fallback option is BizHawk.
- **Claude usage budget** — escalation early-wake must be rate-limited so a pathological
  stuck-loop doesn't burn the budget; cap wakes per window.
- **Legal/ROM sourcing** — user supplies dumps of games they own; Switch emulation is
  deliberately avoided in favor of real hardware.
