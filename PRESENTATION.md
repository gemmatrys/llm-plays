# YouTube Script — "Can Gemma Play Pokémon?"

Format: narrated video, ~7–9 min runtime. Two questions carry the whole video:
**(1) can Gemma play Pokémon, and (2) what does Claude actually add?** Everything else
(hardware specs, console/Switch roadmap, Balatro/BG3) is cut — not video material.

Each beat has: timestamp estimate, **[VISUAL]** (what's on screen), and **VO** (voice-
over, written to be spoken, not read as slide bullets).

**Suggested title:** "Can a Small Local LLM Play Pokémon? (Frontier AI Barely Helps)"
**Thumbnail text idea:** "GEMMA vs POKÉMON" over a Game Boy screen with a red X and a
tiny "+ Claude" in the corner.

**Chapters (for the YT description):**
- 0:00 Hook
- 0:20 The fish that beat Pokémon
- 1:15 Can Gemma actually do this?
- 2:30 Where the small model breaks
- 4:00 What Claude adds
- 5:30 Measuring the gap
- 7:00 The verdict

---

## 0:00 — Cold open / hook

**[VISUAL]** Gameplay footage: Gemma-controlled Game Boy screen playing live, sped up,
in the corner a small HUD showing "AUTONOMOUS — NO HUMAN INPUT." Cut fast, no title
card yet.

**VO:**
"This is a small, local AI model playing Pokémon by itself, right now. No frontier
model, no cloud API making the moves — just a model that fits on one GPU in my closet.
The question I actually want to answer isn't 'can it beat the game.' It's this: once
you let a small model play, how much does a frontier model like Claude even add? Let's
find out."

**[VISUAL]** Title card: "Can Gemma Play Pokémon?"

---

## 0:20 — The fish that beat Pokémon

**[VISUAL]** Archival clip / recreation: the famous "fish plays Pokémon" setup — camera
over a fishbowl, grid overlay, button mapping graphic.

**VO:**
"Quick bit of context. A few years ago, someone rigged a camera over a fish tank, mapped
the tank to a grid, and mapped each grid cell to a Game Boy button. The fish swam around
doing nothing intelligent at all — and it beat Pokémon. Took over three thousand hours,
but it happened. That's the whole founding insight of this project: Pokémon doesn't
require a smart player. It requires a player that never stops playing. So the real
question was never 'is this possible' — a fish already answered that. The question is
what a *good* AI system built on that insight can do faster."

---

## 1:15 — Can Gemma actually do this?

**[VISUAL]** Screen recording: architecture diagram animating in — three layers
(reflex / decision / strategy), then zoom into just the "decision" layer where Gemma
sits. Cut to live gameplay footage of Gemma navigating a route, healing at a Pokémon
Center.

**VO:**
"So: can Gemma play Pokémon? Yes — and here's why I'm confident saying that before
showing you a single hour of footage. The system is built so Gemma doesn't have to be
good, it just has to be better than random some of the time. Two safety nets do the
rest. First, a watchdog: if Gemma stalls or outputs garbage, the system falls back to a
scripted move, then to just standing still, and worst case, to literal random button
mashing — the fish, as a last resort. Second, a save ratchet: the harness forces a save
every few minutes no matter what, so no mistake ever costs more than a few minutes of
progress. Between those two, forward motion is basically guaranteed. That's the boring
half of this video, on purpose."

---

## 2:30 — Where the small model breaks

**[VISUAL]** Screen recording: live log feed scrolling, highlight a repeated failure —
same death, same spot, five times in a row, timestamped. Overlay text: "5 attempts.
Same mistake."

**VO:**
"Here's where it gets interesting. Watch this log. Gemma dies in this cave, in this
exact spot, five separate times. Same wrong turn, same result. A small model making a
decision every couple of seconds has no memory of 'I already tried this and it failed' —
it's not learning mid-run, it's pattern-matching the current frame. It'll also just...
output nonsense sometimes. Invalid moves, contradictory reasoning, confidently wrong
descriptions of what's on screen. None of that breaks the run, because of the fallback
ladder — but it does mean 'never stops moving' and 'plays well' are two very different
claims. That gap — right there — is the whole reason this video has a second question."

---

## 4:00 — What Claude adds

**[VISUAL]** Diagram: "STUCK" flag triggering, a small "escalation" animation, then
Claude's response rendered as a code diff — a new named behavior appearing in a skill
file. Cut to gameplay footage of Gemma cleanly executing that exact puzzle sequence
seconds later, no hesitation.

**VO:**
"This is what Claude is actually for. It isn't watching the run. It gets woken up only
when the system mechanically detects a stall — the screen hasn't meaningfully changed
in twenty minutes, or the same death has happened five times, like the clip you just
saw. Claude looks at the logs and the screenshots once, and it doesn't send back advice
— it writes code. A new scripted behavior: the exact button sequence that solves this
specific puzzle. From that point on, Gemma can run that behavior itself, at full speed,
forever. So the small model supplies volume — thousands of fast decisions an hour — and
the frontier model supplies the handful of moments that actually needed reasoning. Nobody's
watching Claude drive. It shows up, leaves a tool behind, and leaves."

---

## 5:30 — Measuring the gap

**[VISUAL]** Animated chart building live: three lines — "Fish" (flat, slow), "Gemma
alone" (steeper), "Gemma + Claude" (steepest, with visible step-jumps at each Claude
checkpoint). X-axis: hours. Y-axis: progress.

**VO:**
"And because I don't want you to just take my word for any of this, everything's
logged. Every run tracks how many hours Gemma played completely unassisted, how many
times it got stuck, how long each Claude checkpoint took, and — this is the number I
actually care about — how much steeper the progress curve gets right after each
Claude-authored skill lands. You can see it right here: flat stretches while Gemma
grinds alone, then a visible jump the moment a new skill enters the library. That turns
'what does Claude add' from a talking point into a measured delta on a graph, run over
run."

---

## 7:00 — The verdict

**[VISUAL]** Split screen: left = Gemma-alone footage looping through the same failed
attempt; right = full system footage breezing past the same spot. Text overlay: "Same
model. Different result." Then cut to a clean end card with the title again.

**VO:**
"So, can Gemma play Pokémon? Yes — that was always going to be true, the fallback
ladder makes sure of it. The number worth remembering isn't that. It's this: a frontier
model, rationed to a few minutes every several hours, was enough to turn a small local
model's grind into something dramatically faster — without ever touching the
controller itself. That's the actual finding here: you don't need the frontier model
driving. You need it showing up at exactly the right moments. If you want to see the
full run, the graphs, and the architecture behind this, it's all linked below. Thanks
for watching."

**[VISUAL]** End card: subscribe prompt, link to full write-up / GitHub repo.

---

*(Cut from this script: hardware/inference-box details, console/Switch roadmap, and the
Balatro/BG3 stretch goals — save those for a follow-up video or the written report;
see PLAN.md for the full architecture if useful for a pinned comment or description
links.)*
