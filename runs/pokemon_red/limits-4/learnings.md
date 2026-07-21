# limits-4 — run learnings

Leg goal: let the 31B play unattended to find its limits. Shakeout, not the
benchmark. It found three limits on day one:

- **Naming-grid wedge (~15 min).** The prompt claimed B exits the letter grid;
  in Gen 1 B only deletes typed letters. The model dutifully looped B/DOWN/A,
  typing and deleting forever. Escape: A (type a letter), START (jump to ED),
  A (confirm). Hot prompt/goals fix -> escaped within two decisions.
- **The Charmander incident.** After correctly pressing A to inspect a
  pokeball, the model mashed dialogue over Oak's confirmation - a mid-burst A
  accepted CHARMANDER (goals said Bulbasaur), and the naming mash christened
  it "A". Irreversible: the single-slot ratchet had overwritten the pre-choice
  save 30 s after it mattered. The run continues as a hard-mode Charmander
  run. Rule since: confirmation yes/no prompts are single-press only, never
  mashed.
- **False-belief menu wedge, and the first end-to-end I3 fire.** Convinced it
  still had to pick Bulbasaur, the model cycled party/stats menus for ~15 min.
  The behavior-loop detector self-rescued at +12 min, the position detector
  escalated at +17 min, and a checkpoint rewrite of goals.md + memory.md
  unstuck it in one decision.

Also collected here: walkable tilesets harvested live (Red's house 0x01,
Oak's lab 0x11) via the raw-dump drill.

Evening leg (Route 1): terrain rendering corrected to the game's own
block/bottom-left collision convention after flower ground rendered as a
phantom-wall checkerboard; NPC markers, in_battle flag, and [move blocked]
feedback added to the model's context; done_goal self-stamping introduced
after three separate stale-goal slowdowns (lab directions chased on Route 1,
pocket-escape advice followed after escaping — twice). Decision latency
proved to be a confusion meter: 20-38s when goals were clear, 90-124s when
stale/ambiguous. A >90s watcher now pages on it.
