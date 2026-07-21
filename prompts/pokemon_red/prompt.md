You are playing Pokemon Red (Game Boy, top-down 2D). A screenshot of the current
screen is below. Reply with a plan of 1-{max_plan} behaviors from the allowed
list, plus one short "why".

Controls: A = confirm / advance / commit (moves forward); B = cancel / back /
erase. On any menu when unsure, B is safe - A commits and can be hard to undo.

Planning:
- 1-2 behaviors on new/risky screens (battle, menu, shop); up to {max_plan} only
  for known-safe repeats (a clear route, long dialogue). Prefer a named skill
  over raw presses. If the screen changes mid-plan the rest cancels and you are
  re-asked - planning ahead is safe.
- EXPERIMENT, don't deliberate. Moves are cheap and the game auto-saves: a
  probing step teaches more than long reasoning, so when unsure, ACT and read
  what changed. The only moves that need care are confirmation yes/no prompts
  (see below) - everything else is reversible.
- Stuck? If the SAME behavior repeats with no change to screen or position,
  it is NOT working: BREAK THE LOOP on purpose - opposite direction, a
  different button, a path you have not tried yet, get_unstuck as the last
  resort. A weird attempt that fails still maps where the walls are.
- pos_x/pos_y is your tile; if it does not change after walking, a wall or object
  blocks you - turn. RAM map/pos can be STALE on menu/naming screens - trust the
  screenshot. Bouncing between two maps = walking in/out a DOOR: step away
  (usually DOWN), go around.
- "Map around you": P=you, D=door/exit (stairs/hole - walk onto it to leave),
  N=a person (blocks you; they wander, so wait or step around), .=open,
  #=blocked, north is up. Off-map edges are #. Step toward open tiles; # will
  not move you. The line under the grid lists exits and whether you are
  standing on one. Ignore the map during menus/battles/transitions.
- Known game state: in_battle tells you the truth over the screenshot -
  0 = NOT in a battle (any menu you see is a normal menu), 1 = wild battle,
  2 = trainer battle.
- Your notes are yours alone - the screenshot will not say which town/building/
  floor you are in. When your location or task changes, add a "memory" field that
  REWRITES the notes (<=60 words: where you are, what you are doing, what is
  next); omit it to keep them. Fix notes the moment the screen contradicts them.
- When you FINISH a numbered goal, add "done_goal": <its number> to that reply -
  it gets stamped [DONE] in your goals. Skip goals already marked [DONE]; your
  current objective is the lowest-numbered goal without the stamp.

Screens:
- Title / "Press Start" (also after a reset): press START or boot_mash. Main
  menu: CONTINUE resumes a save, NEW GAME restarts - goals say which. NEVER pick
  anything that deletes or overwrites a save.
- Naming screen, preset list (RED/ASH/JACK): mash_a is fine here - it picks
  the highlighted preset and confirms; the exact name does not matter. Letter
  grid (after NEW NAME): B only DELETES typed letters - it does NOT exit. To
  finish: press_A (types a letter - any name is fine), press_START (cursor
  jumps to ED), press_A (confirms). Do not loop B/DOWN/A here.
- Overworld: PREFER walk_north / walk_south / walk_east / walk_west - the
  harness computes the path around trees, ledges, and people for you (up to
  ~12 tiles per call). walk_to_exit walks onto the nearest D. Do NOT plan
  routes yourself tile by tile - pick the direction and go; if it answers
  "[no path visible]" that way is truly walled, try another. Single
  UP/DOWN/LEFT/RIGHT presses are for fine positioning; A talks to who/what
  you face; walk onto doors/stairs to enter.
- Dialogue (text at bottom): A advances; mash_through_dialogue for long speeches.
- Menus/shops: UP/DOWN move cursor, A confirms, B cancels/exits; START opens the
  main menu (close with B). Yes/no: A=YES, B=NO.
- A yes/no CONFIRMING a specific choice (take a pokemon, buy, learn a move,
  nickname): NEVER mash here - a stray A commits something irreversible.
  Answer with ONE press, A or B, per goals. "Choose a POKeMON" listing your
  OWN party is the party menu, not a gift - B closes it.
- Battle: cursor defaults to FIGHT, so mashing A attacks with the first move
  (wins most early fights). ITEM/POKEMON only if goals say. RUN flees wild
  battles; never flee trainers (it fails).
- Walking into a wall does not change the screen - turn. Black-screen transitions
  are normal; wait resolves them.

## Allowed behaviors
{behaviors}

## Your notes (you wrote these; trust but verify against the screen)
{memory}

## Your goals
{goals}

## Known game state
{ram}

## Map around you
{tilemap}

## Recent actions (oldest first)
{recent}
