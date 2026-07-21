# Benchmarks — "How fast can Gemma beat Pokémon? (with Claude's help)"

The essay title is deliberate: the *local* model does the playing; Claude appears only
as the rationed strategy layer, and its entire contribution is itemized (checkpoint
count, tokens). The headline question is comparative: not *can* an LLM system beat
these games (the fish settled that), but *how fast*, against every famous prior attempt.
This file defines the baselines, the measurement rules, and the comparison design.
The essay is the deliverable; every number in it should trace back to `metrics.jsonl`.

## 1. The wall of baselines (prior art)

| Contender | Game | Result | Time | Notes |
|---|---|---|---|---|
| **Speedrunner (human)** | Red | champion | ~2 h | lower bound, not a fair target |
| **Casual human child** | Red/Blue | champion | 20–40 h | the "normal" reference |
| **Twitch Plays Pokémon** (2014) | Red | champion | 16 d 7 h ≈ **391 h** | 1.16 M humans, pure chaos input |
| **The fish** (Mutekimaru, 2020) | Sapphire | champion | **3,195 h** | 4 fish named Maurice, random input; found a new glitch |
| **Peter Whidden's RL agent** (2023, the famous video) | Red | reached Cerulean / Mt. Moon | 50,000+ h of training play | never beat the game in the video; later arXiv work went further |
| **Gemini 2.5 Pro** (May 2025) | Blue | champion | **813 h**, 106,505 steps | first frontier-LLM completion |
| **Claude Opus 4.5** (2025) | Red | incomplete at ~300 h, 48,854 steps | — | e.g. 78 h stuck in Mt. Moon on one run |
| **Claude Opus 4.7** (2026) | Red | champion | see run reports | first Claude completion |

Takeaways that shape our design:
- The fish's 3,195 h is the **liveness-only** number. Twitch's 391 h shows what noisy
  crowd "intelligence" buys. Gemini's 813 h shows a frontier LLM *alone* is slower than
  the crowd — per-step latency dominates. **The gap we attack is latency**: a local
  LLM decides in seconds, not tens of seconds, and scripted skills decide in frames.
- Every prior LLM run used a bespoke scaffold, making cross-run comparisons
  apples-to-oranges (widely noted re: Claude vs Gemini harness differences). Our
  three arms (below) share **one harness**, which is the scientifically clean part.

## 2. Measurement rules (so our numbers are defensible)

Clocks — always report all of these, because baselines mix them freely:
1. **Wall-clock hours**: start of run to champion, pauses included. Headline number;
   what fish/TPP/Gemini figures are.
2. **Emulated game hours**: emulator runs at 1× (no fast-forward) so wall-clock and
   game-clock stay comparable to the baselines. If we ever fast-forward waiting
   animations, report both clocks and say so.
3. **Decisions**: count of harness ticks (≈ "reasoning steps" in the Gemini/Claude
   run reports).
4. **Frontier-model budget**: Claude checkpoint count, wall time, and tokens. This is
   our differentiator: prior LLM runs spent frontier tokens on *every step*; we spend
   them on checkpoints only. "Claude beat Pokémon using N checkpoint calls" is the
   efficiency headline.

Rules:
- One continuous run per result; hard resets and loadstates are allowed (logged), but
  human intervention ends the run (restart from scratch or mark the run assisted).
- Harness restarts (hotfix, recovery) are logged (`harness_start` in metrics.jsonl).
  Wall-clock keeps counting through the downtime — the headline stays
  baseline-comparable — but decision-rate/health metrics are computed over **active
  harness hours** (sum of in-segment spans), so a restart never deflates them.
- Report the **progress curve** (badges vs hours), not just the total — that's where
  "Claude escaped Mt. Moon in 2 h vs 78 h" stories live. Badge timestamps come from
  RAM-change milestones in `metrics.jsonl`.
- Per game, publish: total hours, decisions, rung distribution (what % of decisions
  were LLM vs scripted vs fish), escalation count, Claude budget.

## 3. The three-arm comparison (attribution)

Same harness, same game, three configurations:

| Arm | Config | Answers |
|---|---|---|
| A — Fish | `--policy fish` | our reproduction of the 3,195 h baseline (per game) |
| B — Local only | `--policy llm`, checkpoints disabled | what a $949 GPU buys over the fish |
| C — Full system | local LLM + Claude checkpoints | what Claude's strategy layer buys over B |

Arm A can be time-boxed (e.g. 200 h, extrapolate from the progress curve) rather than
run to completion — we don't need to burn 3,000 hours re-proving the fish.

## 4. The game ladder

**Stage 1 — every mainline Pokémon** (Gens 1–9). Same genre, rising complexity;
per-gen table of hours/decisions/Claude budget is the essay's centerpiece.

**Stage 2 — Balatro.** Chosen because it's the *anti-fish* game: turn-based with zero
reflex demands (architecture fits perfectly) but random input essentially never wins a
run — rung 4 is useless, so Arm A flatlines and the LLM must carry entirely. First PC
target: needs a window-capture Eyes driver and an OS-level mouse/keyboard Hands driver;
no RAM map, so vision/OCR does progress tracking (score, ante, money are big on-screen
numbers — friendly OCR). Fixed seeds + stake level make runs reproducible. Metric
shifts from hours-to-credits to **win rate and antes-per-run** vs published human
win-rate stats.

**Stage 3 — Baldur's Gate 3.** The long-horizon boss: turn-based combat (good) but
real-time exploration, camera control, deep dialogue/quest state, and a decision space
no skill library fully covers. Native save system makes the ratchet natural. This is
where the Claude checkpoint layer either shines (quest-level planning, party builds)
or the project finds its honest ceiling. Metric: story-completion hours vs the ~75–100 h
casual human playthrough, plus quest-completion curve.

## 5. Essay skeleton — "How fast can Gemma beat Pokémon? (with Claude's help)"

1. The fish proved persistence suffices (3,195 h). Twitch proved crowds are faster
   (391 h). Gemini proved a frontier LLM alone is *slower than the crowd* (813 h).
2. Claim: the right architecture — cheap local decisions, frame-rate skills, frontier
   intelligence only at checkpoints — beats all three numbers, per generation.
3. Method: the harness, the three arms, the measurement rules (§2–3).
4. Results: per-gen table + badges-vs-hours curves + rung distribution.
5. The money graph: hours-to-champion across fish / TPP / Gemini / Claude-alone /
   this system; second graph, frontier tokens per completion.
6. Where it breaks: Balatro (no fish floor), BG3 (no skill library coverage).
