# Master plan — Pokémon Red, Bulbasaur run

CHECKPOINT-VOICE ONLY; the model NEVER reads it. The quest tree itself
lives at prompts/pokemon_red/quests.yaml (moved 2026-07-22, user
decision): the HARNESS ingests it, feeds one quest at a time with the
act ladder and time budgets, and records the model's done/coach marks;
the checkpoint authors and refines its content. This file is the
generatable companion — the reasoning, routes, data prep, and risk
briefs BEHIND each act's quests, so refinement at act boundaries copies
from here instead of re-deriving under alarm pressure. The plan can be
wrong; the quests.yaml structure is what the run depends on.

How to use — REFINE EARLY, NOT AT THE ALARM (acts auto-advance on the
closing stamp, so an unrefined act plays its GUESS facts live): refine
act N+1 while act N is in its GYM quest, the natural pause. Then at
each act_stamped alarm:
1. Validate the closing act's verify line against RAM/screen (the
   verify anchors live in quests.yaml per act; the alarm echoes them);
   un-stamp in the run's quests.yaml if the evidence disagrees. Also
   verify the team's ACTUAL move slots against the forget table below —
   one missed learn event silently breaks every later attack_N rule.
2. If act N+1 was not yet refined, do it NOW from this file's section
   A: fix guesses fetched or verified since, audit for jargon (raw
   field names never; verified coordinates are fine — location phrases
   exactly as maps.yaml renders them). Editing protocol: only at/after
   current+1, never before the current quest (positional numbering);
   clear answered coach flags back to todo. Status marks and the
   ladder rendering are mechanical — do not hand-edit numbering or
   done-collapse.
3. Apply section B waypoints (keep the live waypoints.yaml SMALL — add
   the act's block, prune the previous act's one-problem scaffolds;
   crossed-map history is recoverable from git).
4. Do section C data prep BEFORE the act needs it (marts, tilesets,
   state fields, skills) — an unharvested tileset makes every walk
   macro a silent no-op.
5. Read section D (risk brief) so alarms are answered from a plan, not
   from scratch.
6. VERIFY THE PUBLISH per edit (standing instruction — `kind:"publish"`
   metric or `git log live/<run-id>`).

Marking convention (from the limits runs):
- VERIFIED — from pret/pokered warp/object tables, or confirmed live in
  a limits run's log. Warp/object-table coords are trustworthy for
  WHERE things are; never for behavior (the warp table lies about
  enterability — the forest gate (4,0) lesson).
- GUESS — offset math, walkthrough recall, or my memory of the game.
  FETCH FROM THE SOURCE at act prep (user rule 2026-07-22: prefer
  fetching pret/walkthrough data over writing from recall — the mart
  table and map-name gaps are already fetched and de-GUESSed); eyeball
  coordinates at first crossing, promote with the live log.
- Data tables (marts, names, collision lists) are pre-ingested from
  pret/pokered; LIVE verification is reserved for BEHAVIORAL claims
  (the 0x55 fence, ledges, anything one-way or conditional).

---

## Standing drills — named learnings, referenced by every act

These are cited by name below; the full accounts are in LEARNINGS.md.

- LABEL-FIRST CONFIRM: at any take/buy/learn/choose prompt, ONE press
  after READING what the screen names. Position assumptions banned (the
  Charmander incident: a mash answered Oak's YES/NO mid-burst).
- PRUNE-ON-STAMP: stamped goals collapse to one-line stubs immediately.
- RULE-SILENCING: when a stretch predictably disables a rule, the goal
  says so ("no POTIONs until Pewter — Potion rules do not apply on this
  walk"). Inapplicable rules have a measured deliberation price (+47%).
- YIELD CLAUSE: any rule that can co-trigger with a goal drill defers
  itself ("a fight the current goal does not say how to handle: ...").
- SHOP FOCUS TRAP + QUANTITY RENDER-WAIT: buy skills checkpoint every
  screen through the judge; quantity boxes need a render wait (x5
  asked, x1 bought). buy_<item>_x<n> is minted from marts.yaml — the
  mart entry MUST exist before the town is reached.
- MENU FALSE POSITIVES: nav_ineffective and the confusion detectors
  fire falsely in menus/dialogs (five in one day). When an alarm
  arrives, check "was it in a menu?" before acting on it.
- LEDGE ONE-WAY: hopping down is fine, climbing back is impossible.
  Goals must say which side of a ledge line the route lives on; a ledge
  fall restarts the leg (goal text carries the restart instruction).
- PROBE-AFTER-TWO: when navigation prose fails twice, STOP theorizing
  and probe per-tile walkability at explicit map coords (scratchpad
  probe_area.py pattern over a second bridge connection). Screenshots
  and the block render are ambiguous at 2x2; the tile dump is the only
  trustworthy view. Better: pre-derive walkable grids offline from pret
  block data before the act arrives (see per-act data prep).
- MICRO-GOAL FORM: one tangible action; sub-goals (a)(b)(c) each with a
  CHECK the model validates against its state lines; progress kept in
  the model's NOTES ("N: a done, working b"), notes fixed when the
  screen disagrees; an explicit DONE line in state-line vocabulary; a
  "Time budget: N minutes." line. Cardinal sub-steps anchor to landmark
  BEARINGS by default; VERIFIED coordinates are also fair game in quest
  text (user 2026-07-22: humans follow walkthrough coordinates too —
  only GUESSED coordinates burned us). Doors end in a single press — walks stop
  BESIDE doors, only a raw press enters. (enter_door_above and
  walk_to_exit were REMOVED from the vocabulary 2026-07-22: one-problem
  scaffold and a two-bans-needed trap respectively; rooms are left by
  walking onto the doormat — can_move announces doorways — plus one
  edge press. Between buildings: landmark walks or plain walks.)
- BELIEVE-AND-STAMP: the model stamps done_goal on belief; the next
  goal feeds at once; goal_stamped brings the coach in async to
  validate against the act's verify anchor (RAM first — the alarm is
  not evidence; three false stamps in one day).
- COACH FLAG: doubt is free; every "COACH:" note gets answered. Wrong
  flags cost minutes, suppressed doubt costs hours.
- WIRE SEQUENCES, TEACH ONE-PRESSES: prose multi-press drills execute
  as one press per decision and drift. Anything deterministic once the
  intent is known becomes a skill; conversations stay with the model
  under the choice-stop guard.
- EVOLUTION SCENES: pressing B during the evolving animation CANCELS
  the evolution. Every act whose level gate crosses an evolution level
  carries a rule: "when the screen says your Pokemon is evolving, wait
  it out — do not press B."
- MOVE-LEARN DRILLS: a level-up move prompt is an irreversible choice
  mid-battle. Each act pre-writes the expected learn events with the
  exact answer ("learn X, forget Y" or "do not learn"). The forget
  table lives in the cross-cutting TEAM PLAN section — keep slots
  predictable so the attack_N mapping in Rules stays true.

---

## ACT 0 — Bulbasaur and the errand loop (Pallet/Viridian)

Tree verify (goal_stamped anchor for the act): team line shows
BULBASAUR; Pokedex obtained; owned species >= 3; POKE BALLs in bag.

The run-ready quests are act0 of prompts/pokemon_red/quests.yaml —
this section's A-part in quest form, vocabulary-audited. This section
carries the reasoning and the checkpoint-side annotations.

### A. Micro-goals (DRAFT — the quests.yaml act0 copy is authoritative)

1. Boot a NEW GAME. Fresh cartridge state: the title menu has no
   CONTINUE (rule-silencing line needed — prompt.md says "on a title
   screen: CONTINUE"; the goal must override: "this is a brand-new
   game — pick NEW GAME"). Mash A through Oak's welcome lecture.
   At the NAME screen: press DOWN once then A to take the first
   ready-made name; if a screen full of letters opens anyway, escape
   with press_A, press_START, press_A (B only deletes letters — the
   naming-grid lesson). Same drill for the rival's name.
   DONE: location reads Red's House 2F. Budget 15m.
2. Walk downstairs and out (stairs are a walk-onto warp; the house
   door exits south over the doormat). Door trap note in Rules: on a
   doorstep, UP walks back in.
   DONE: location reads Pallet Town. Budget 5m.
3. Walk NORTH toward the tall grass at the town's top edge. Oak stops
   you himself and walks you to his lab (scripted). Mash the speech.
   CHECK: you never reach Route 1 — being stopped is the plan.
   DONE: location reads Professor Oak's lab. Budget 10m.
4. STARTER — the drill of the run (label-first; the limits-4 mash took
   Charmander). Three Poke Balls sit on the table. At EACH ball: press
   A, READ the dialogue — it names the species. Only when the screen
   names BULBASAUR answer YES (one press). Any other name: answer NO
   (one press B) and step to the next ball. Nickname prompt: NO.
   Sub-goals: (a) read a ball's label; (b) confirm only on BULBASAUR;
   (c) decline the nickname. Notes protocol: "4: read ball 1 = CHAR,
   trying next".
   DONE: team line shows BULBASAUR. Budget 15m.
   [Checkpoint annotation: ball order on the table is deliberately not
   asserted — the drill makes order irrelevant. GUESS from pokered
   object data: the balls sit in a row on the lab table; rival picks
   AFTER us and always takes Charmander (our counter).]
5. Rival battle 1 (his CHARMANDER L5 vs our L5). attack_1 (TACKLE)
   every turn; his Growl turns are free. A loss costs half our ~¥3000
   and is acceptable — do NOT flag a loss, just carry on.
   DONE: the battle is over and location still reads the lab. Budget
   15m.
6. Leave the lab (south over the mats), walk north out of Pallet onto
   Route 1 through the top-edge gap, then the length of Route 1 north.
   No trainers on Route 1; wild PIDGEY/RATTATA — fight for XP or flee,
   either is fine (yield to later catch goals: do not throw balls yet,
   we have none).
   DONE: location reads Viridian City. Budget 20m.
7. Viridian Mart: enter (the "Viridian Mart door" bearing), walk to
   the counter, talk — the clerk hands over OAK'S PARCEL unprompted.
   DONE: "[bag: +1 OAK's PARCEL]" happened. Budget 10m.
8. Return to Pallet (south gap, Route 1 south — the LEDGES on Route 1
   hop DOWN only; going south they are shortcuts, never try to climb
   one), into the lab, talk to Oak.
   DONE: "[bag: -1 OAK's PARCEL]" happened and the POKEDEX was handed
   over (rival scene plays). Budget 20m.
9. Back to Viridian (north again). Buy at the mart: 5 POKE BALLs, 3
   ANTIDOTEs (buy_poke_ball_x5, buy_antidote_x3 — minted skills carry
   the clerk talk; the shelf has no POTIONs — rule-silencing: "no
   POTIONs exist on this shelf; Potion rules do not apply until
   Pewter").
   DONE: bag shows 5 POKE BALLs and 3 ANTIDOTEs. Budget 15m.
10. CATCHING, Route 1 grass: weaken with TACKLE to yellow/red HP, then
    use_poke_ball. Target: PIDGEY and RATTATA (one each). Poke Balls
    only work on WILD battles. If a ball misses, chip once more and
    throw again.
    DONE: owned count reads 3 or more kinds. Budget 30m.
11. CATCHING, Route 22 (west of Viridian): one NIDORAN (either kind).
    The RIVAL may appear near the gate and demand a fight (optional
    encounter, GUESS timing): fight him with TACKLE, a loss is
    acceptable — do not flee toward the gate mid-battle.
    DONE: owned count reads 4 or more kinds. Budget 30m.
12. Heal at the Viridian Center (walk-to-counter, ONE press A on the
    nurse's yes/no, mash the rest). Stay near the Center; new goals
    arrive next.
    DONE: team at full HP and location reads Viridian Pokemon Center.
    Budget 10m.

### B. Waypoint prep (initial waypoints.yaml at run creation)

All Pallet/Viridian/Route-1 coords were LIVE-VERIFIED in limits runs
(recovered from git history of runs/pokemon_red/limits-4/waypoints.yaml
@ a58a70d) — resurrect, do not re-derive:

```yaml
waypoints:
  # --- Act 0 (all VERIFIED live in limits-3/4 unless marked) ---
  Oak's lab door: {map: 0, x: 12, y: 11}
  Oak: {map: 40, x: 5, y: 2}            # GUESS ±1, adjacent talk works
  the grass at the top of town: {map: 0, x: 10, y: 1}   # GUESS: Route 1 gap column
  gap to Pallet Town: {map: 12, x: 10, y: 35}
  gap to Viridian: {map: 12, x: 11, y: 2}
  Viridian Mart door: {map: 1, x: 29, y: 19}
  Viridian Center door: {map: 1, x: 23, y: 25}
  south gap to Route 1: {map: 1, x: 21, y: 35}
  gap to Route 22: {map: 1, x: 0, y: 17}   # GUESS: west road row; eyeball
```

Prune at Act 1: lab/Oak/grass scaffolds (one-problem); keep the
Viridian doors and gaps (durable — Act 9 returns here).

### C. Data prep

- marts.yaml: Viridian (map 42) already ingested. Nothing new.
- tiles.yaml: overworld, Red's house, lab, mart, pokecenter all
  harvested in limits runs. Blue's house / private-house tileset
  (HOUSE) may be unharvested — irrelevant, no goal enters one.
- NEW STATE FIELD (add before run start): owned-species count.
  Provider `_field_owned_kinds` reading the Pokedex owned bitfield.
  Serving criterion justification: the number of kinds ever owned is
  not visible on any frame outside the Pokedex menu and cannot be
  inferred from prompt+goals; catch goals' DONE lines need it ("owned
  count reads 3 or more kinds"), and the Act 4 Flash gate (10 owned)
  is checked against it for four acts. state_lines sentence: "You have
  owned N kinds of Pokemon." + STATE_FIELDS order entry.
- SKILLS: use_poke_ball must fire in battle (items.py battle path —
  use_potion's battle flow is still UNFIRED from limits-4; the catch
  goals here are its first live test class. Watch the first firing).
- Savestates: pin slot 2 immediately after goal 4 validates (BULBASAUR
  on team, pre-rival) — the starter is the one truly irreversible
  choice in the act.

### D. Risk brief

Wedge classes expected:
- Mash-through-the-confirm (Charmander class) at goal 4 and the
  nickname prompt. Drill: label-first, ONE press. Coach: validate the
  goal-4 stamp against the party species RAM immediately — if the team
  line says anything but BULBASAUR, STOP THE RUN (loadstate slot 1/2;
  this is the one place savestate rollback is pre-authorized, budgeted
  minutes not hours).
- Naming-grid wedge (B-loop). Drill in goal 1; the A-START-A escape is
  live-verified.
- Door trap (doorstep UP re-enters) — Rules line.
- Ledge falls on Route 1 southbound — geometry favors us (shortcuts);
  northbound the goal says never climb.
- Ball-throw in trainer battle (balls are simply lost) — Rules line +
  yield clause in the battle rule.
- False stamps on catch goals ("I caught it" when the ball shook out).
  The owned-count state line makes the DONE check objective; coach
  validates stamps against the Pokedex RAM.
- Detector noise: goals 7-9 are menu-heavy; expect menu false
  positives from nav_ineffective/confusion detectors.
Alarms: goal_overtime on 10/11 (catch RNG) — response is to lower the
target ("owned >= 3" is the act verify, goal 11 can be cut), never to
extend silently. goals_complete after 12 → Act 1 mint.

### E. Team/level gate at act close

BULBASAUR L6-8 (rival + Route 1 XP), PIDGEY, RATTATA, NIDORAN on the
roster (catches are roster-fillers and Flash-count fodder; they never
battle on purpose). Cash ≥ ~¥1500 after the ball/antidote buy.

---

## ACT 1 — BOULDER badge (Brock, Pewter)

Tree verify: RAM badges 0 -> 1 (BOULDER bit); TM34 bag event.

### A. Micro-goals (DRAFT — renumber at mint)

1. Walk north through Viridian to the top edge (the "gap to Route 2"
   bearing). An old man mid-town demonstrates catching (scripted once,
   post-parcel): mash his speech, decline nothing.
   DONE: location reads Route 2. Budget 10m.
2. North on Route 2 to the forest gate door (the "forest gate door"
   bearing), through the gate building: cross the room with plain
   walks and step through the FAR doorway (the standing gate drill).
   DONE: location reads Viridian Forest south gate building, then
   Viridian Forest. Budget 10m.
3. FOREST, leg 1 (the maze lesson: the forest only opens northward on
   the EAST side — do not chase the exit bearing, it crosses tree
   walls). Walk to "the path north (east side)" bearing.
   CHECK: that bearing reads "you are here" or 1-2 tiles.
   Budget 15m.
4. FOREST, leg 2: north then west along "the top corridor" bearing.
   CHECK: bearing satisfied. Budget 15m.
5. FOREST, leg 3: down the west lane past "the west side path"
   bearing toward "forest exit corner". A dropped item sits just off
   the west lane (the "a dropped item" bearing) — pick it up ONLY if
   it reads 1-2 tiles while on the path (opportunistic, never a stop:
   the walled-Potion lesson).
   CHECK: "forest exit corner" reads 3 tiles or less. Budget 15m.
   [Goals 3-5 are ONE goal in the mint if the model handles legs well
   in notes ("forest legs done: 1,2") — the limits-4 false-stamp on
   leg flip-flops says keep them separate. Judgment call at mint.]
6. GRIND + CATCH in the forest: stay in the grass near the exit
   corner. Targets, in priority order: (a) catch PIKACHU if one ever
   appears (rare; it is the run's electric answer — keep at least 2
   balls for it the whole act); (b) catch one WEEDLE or CATERPIE
   (cheap species count); (c) fight everything else for XP: TACKLE.
   Bug catcher trainers on the path pay out and give the best XP —
   fight the ones that stop you.
   Level checkpoints in notes: "6: L9", "6: L11"...
   DONE: team line shows BULBASAUR L13 or higher AND VINE WHIP on the
   move list (learned at 13 — it has a free slot, no forget prompt).
   Budget 90m. RULE-SILENCING: "no POTIONs in the bag until Pewter —
   heal by walking back to the Viridian Center only if HP goes red
   twice" (the forest is a no-Potion stretch; poison → use_antidote
   immediately, that is what the 3 are for).
7. Exit north: the corner doormats, through the north gate building
   (same far-door drill), Route 2 north to the "gap to Pewter"
   bearing. Do NOT enter the cave door on the way (Diglett's Cave —
   its time is Act 4).
   DONE: location reads Pewter City. Budget 15m.
8. Heal at the Pewter Center (the "Pewter Center door" bearing).
   DONE: team at full HP, location reads Pewter Pokemon Center.
   Budget 10m.
9. Buy at the Pewter Mart (the "Pewter Mart door" bearing): POTIONs
   until the bag holds 6 (buy_potion_x6 or as money allows), keep
   ≥¥600 in reserve. Every "[bag: +N ...]" event is the proof.
   DONE: bag shows 6 POTIONs (or money at the reserve floor). Budget
   15m.
10. Walk to "the doormat below the Gym entrance" bearing. Route (from
    the limits-4 tile probe — the yard opens ONLY from the west):
    (a) from the Center, north up the west column;
    (b) east into the yard along the row;
    (c) stand on the doormat.
    CHECK each leg in notes. The south edge of the yard row is a
    ONE-WAY LEDGE — a fall restarts from (a); the goal says so.
    FALLBACK if two prose fixes fail (probe-after-two): abandon the
    yard, walk EAST along the main road toward "the road east to
    Route 3" — the badge-gate man stops you and DRAGS you to the gym
    himself; mash his speech and do not walk away.
    DONE: the doormat bearing reads "you are here". Budget 20m.
11. Enter the gym: one step UP through the door above (press_UP).
    DONE: location reads Pewter Gym. Budget 5m.
12. Reach BROCK (the "Brock" bearing): the JR TRAINER on the way is
    effectively mandatory (trainer battles cannot be fled) — VINE
    WHIP (attack_4) his DIGLETT and SANDSHREW (both take double).
    Below half HP after: use_potion.
    DONE: the "Brock" bearing reads 2 tiles or less. Budget 15m.
13. Beat BROCK: talk to him. GEODUDE L12, ONIX L14 — both rock/ground:
    VINE WHIP (attack_4) two-hit-KOs each. His side barely scratches
    Bulbasaur (resists rock AND ground... [checkpoint: ground is
    neutral vs grass/poison, rock attacks are the threat and Onix's
    Bide the gimmick]). When ONIX is "storing energy" (BIDE — returns
    double the damage taken): that turn is the perfect use_potion
    turn, or keep attacking to end it fast. Loss protocol: blackout
    costs half your money — heal and march back; after TWO losses,
    grind the forest to L15 and return.
    DONE: the badge announcement happened and "[bag: +1 TM34]".
    Budget 45m.

### B. Waypoint prep

Resurrect from limits-4 git (@ a58a70d), all VERIFIED live except as
marked:

```yaml
  # --- Act 1 ---
  gap to Route 2: {map: 1, x: 18, y: 0}
  south gap back to Viridian: {map: 13, x: 8, y: 71}
  forest gate door: {map: 13, x: 3, y: 43}
  doorway into the forest: {map: 50, x: 4, y: 0}
  the path north (east side): {map: 51, x: 31, y: 30}
  the top corridor: {map: 51, x: 25, y: 11}
  the west side path: {map: 51, x: 2, y: 18}
  a dropped item: {map: 51, x: 12, y: 29}     # POTION; key mute on purpose
  forest exit corner: {map: 51, x: 1, y: 0}
  doorway out to Route 2: {map: 47, x: 4, y: 0}
  gap to Pewter: {map: 13, x: 8, y: 0}
  Pewter Center door: {map: 2, x: 13, y: 25}
  Pewter Mart door: {map: 2, x: 23, y: 17}
  Pewter Gym door: {map: 2, x: 16, y: 17}
  the doormat below the Gym entrance: {map: 2, x: 16, y: 18}
  the road east to Route 3: {map: 2, x: 38, y: 17}   # GUESS (limits-4)
  Brock: {map: 54, x: 4, y: 1}
```

NOTE: the forest Poke Ball item at (1,31) was collected by limits-4 —
this is a NEW SAVE: both forest items respawn. Waypoint only the west-
lane one as before; the (25,11)-adjacent ANTIDOTE sits in a trainer's
sight line (leave unwaypointed, as limits-4 did).

### C. Data prep

- Pewter walkable map OFFLINE DERIVATION (the standing run-2 item, do
  it NOW, before launch): render the full Pewter City walkability from
  pret block data (blocks -> blockset -> per-tileset collision), and
  re-verify the west-column yard route as drawn in goal 10. Kills the
  gym-yard guess-probe loop as a class. Extend the same script to any
  town/gym this plan flags for probing (it becomes THE probe tool).
- marts.yaml: Pewter (56) ingested. tiles.yaml: forest, gate, gym,
  museum all present from limits runs. Nothing new expected.
- Skills: attack_1..4, flee_battle exist; use_potion battle path may
  get its first firing at Brock — the limits-4 watch item transfers
  here. (Gym entry is a plain press_UP on the doormat now.)
- Savestates: re-pin slot 2 healed-pre-gym after goal 8 (Brock loss
  recovery insurance; in-game blackout recovery remains the actual
  loss path).

### D. Risk brief

- Forest maze bearing-chase (2h wedge class): the leg structure + "do
  not chase the exit bearing" line answers it. Coach: loop_detected in
  the forest → check which leg the notes claim, fix notes/goal, do not
  trust nudges alone (all three limits-4 forest fires needed route
  fixes).
- False stamp on the exit goal ("Exit the forest" stamped while
  inside — happened live). Validate location RAM on every forest-goal
  stamp.
- Pikachu hunt overtime: goal 6's budget is the act's biggest; if
  overtime fires with L13 reached but no Pikachu, move on — Pikachu
  has a fallback (Voltorb, Act 4 prep) for the Flash slot but not for
  Thunderbolt; note the miss in the tree's team-plan ledger.
- Gym yard entry: pre-derived map (data prep) should settle it; if
  live contradicts, probe-after-two, then the escort fallback is
  KNOWN-GOOD (it drags to the gym unconditionally pre-badge).
- Brock BIDE: the use_potion-on-Bide line; watch the first battle
  use_potion firing (skill checkpoint feedback tells if it misfired).
- goal_stamped anchor for the act: badges byte 0x00 -> 0x01. The
  limits-4 BOULDERBADGE false stamps (twice, at badges=0) are the
  exact class this anchor kills.

### E. Team/level gate

BULBASAUR L13-14 with VINE WHIP at the Brock fight; Pikachu if lucky.
Cash after Potions ≥ ~¥600 (Brock pays ~¥1400 — restock after).

---

## ACT 2 — CASCADE badge (Misty, Cerulean)

Tree verify: badges byte has CASCADE; TM11 bag event.

The stretch3-draft.md package (checkpoint-reviewed 2026-07-21) is the
seed for this act — its waypoint block is pret-verified and its route
text is sound; the goals below are its micro-goal restructuring, with
Charmander swapped for the Bulbasaur line.

### A. Micro-goals (DRAFT)

1. Restock at the Pewter Mart before leaving (no shop again until the
   far side of the mountain): POTIONs to 6, 1 ESCAPE ROPE, 2
   ANTIDOTEs, and 2 POKE BALLs only if money allows (priority order,
   skip what you cannot afford — every "[bag: +N]" event is proof).
   DONE: the list is bought or money is spent down to ~¥100. Budget
   15m.
2. Leave Pewter east (the "east gap to Route 3" bearing) onto ROUTE 3.
   Eight trainers line this road; the ones facing the path stop you —
   fight: VINE WHIP by default, TACKLE for bugs and birds [checkpoint:
   bug and flying both resist grass — the Rules carry "bugs and birds:
   attack_1"]. Potion below half.
   DONE: location reads Route 3 and the road's trainers are behind
   you (no one stops you walking east). Budget 45m.
3. At the east end climb north to ROUTE 4; heal at the Center by the
   cave (the "Center by the cave door" bearing). Inside, a man sells
   a MAGIKARP for ¥500: ONE press B, do not buy.
   DONE: team at full HP, location reads Mt. Moon Pokemon Center.
   Budget 15m.
4. Enter MT MOON (the "cave entrance" bearing) at full HP. Wild ZUBAT
   and GEODUDE: flee what you do not need (flee_battle) — but catch
   ONE ZUBAT and ONE PARAS if balls allow (species count; Paras
   appears on the lower floors). Two dropped items on 1F are on the
   way (bearings) — face, A, read the bag event. The way down is the
   northwest ladder (the "ladder down (1F northwest)" bearing); the
   HIKER standing over it must be beaten.
   DONE: location reads Mt. Moon B1F. Budget 45m.
5. Cross B1F (the "ladder down to the bottom floor" bearing) to B2F.
   ROCKETs fight you on the way. At the fossil shelf a SUPER NERD
   guards two fossils: beat him, then take the LEFT one and answer
   its question with ONE press A (label-first; either fossil is
   strategically worthless this run — deterministic beats open
   choice). Leave by "ladder out past the fossils" then "daylight
   exit to Route 4".
   DONE: location reads Route 4 and "[bag: +1 DOME FOSSIL]" (or
   HELIX) happened. Budget 45m.
6. Walk EAST the length of Route 4 into CERULEAN (the "gap to
   Cerulean" bearing). The ledges beside the road are one-way SOUTH
   hops — dropping is fine, climbing back is impossible; keep east on
   whichever level you land.
   DONE: location reads Cerulean City. Budget 15m.
7. Heal at the Cerulean Center. EVOLUTION note: Bulbasaur evolves at
   L16 — when the screen says it is evolving, WAIT — do not press B
   (B cancels evolutions).
   DONE: team at full HP, location reads Cerulean Pokemon Center.
   Budget 10m.
8. Grind to L18+ if not there (Route 4 ledge grass beside the city,
   or the Nugget Bridge grass north — do NOT cross the bridge's
   trainers yet, that is the next act's gauntlet). IVYSAUR by 16.
   DONE: team line shows IVYSAUR L18 or higher. Budget 45m.
9. Misty's gym (north part of town): one swimmer trainer first.
   MISTY: STARYU L18, STARMIE L21 — both water: VINE WHIP takes
   double. STARMIE's BubbleBeam hits hard: Potion below half, keep
   attacking. Loss protocol as always (two losses → grind to L20).
   DONE: badge announcement + "[bag: +1 TM11]". Budget 45m.

### B. Waypoint prep

Apply the stretch3-draft block verbatim (it is already pret-sourced;
GUESS marks preserved: Pewter east gap, Route 3 climb, Route 4
Cerulean gap need first-crossing eyeballs). Add:

```yaml
  Cerulean Center door: {map: 3, x: 19, y: 17}   # VERIFIED (warp table)
  Cerulean Gym door: {map: 3, x: 30, y: 13}      # GUESS - warp table at prep
  Cerulean Mart door: {map: 3, x: 25, y: 25}     # GUESS - warp table at prep
  Misty: {map: 65, x: 4, y: 3}                   # GUESS - object table at prep
```

Prune at apply time: all Pewter scaffolds except the three door
waypoints (Act 9 does not return here; "the road east to Route 3"
becomes the act-2 exit and then prunes).

### C. Data prep

- tiles.yaml: CAVERN already ingested (stretch3 review). Cerulean
  interiors are pokecenter/mart/gym/house — all known tilesets.
- marts.yaml: Cerulean (67) INGESTED 2026-07-22 (fetched from pret
  marts.asm, whole-game table). REPEL matters: Act 4 buys them here
  or in Lavender for Rock Tunnel.
- Species/moves data already full-table. Nothing else.
- Savestates: pin slot 2 at the cave mouth pre-entry (stretch3 risk
  #3), re-pin healed-pre-Misty.

### D. Risk brief

- PP exhaustion underground: Escape Rope bought in goal 1 + the
  flee-wilds line; coach reads party PP at every look — both attack
  moves near 0 mid-cave → hot-edit the goal to force the rope.
- Poison + blackout spiral: two-blackout circuit breaker in goal
  text; antidotes restocked in goal 1.
- Irreversible prompts: fossil and Magikarp are ONE-press lines;
  choice-stop guard covers trailing steps.
- Zubat catch vs flee tension: the catch clause yields ("if balls
  allow") — watch for the model burning every ball; Rules keep "keep
  the last ball for PIKACHU" phrasing from limits-4? NO — Pikachu is
  forest-only and behind us; rewrite the reserve line to "keep 2
  balls spare past Mt Moon" (Oddish/Abra on Routes 24/25 next act).
- Evolution-cancel (B during the scene) — goal 7 note + Rules line
  for the whole run.
- Misty's Starmie is the first real damage race; goal_overtime on 9
  → response: grind gate to L20, X Defend NOT in plan (no buys
  off-list).
- goal_stamped anchor: badges byte bit 2 (CASCADE).

### E. Team/level gate

IVYSAUR L18-20 at Misty. Zubat/Paras add species 5-6 (7 with
Pikachu). TM11 held (no teach — Lapras gets better later). Fossil
held (never revived this run — it would cost a Cinnabar detour).

---

## ACT 3 — THUNDER badge (Lt. Surge, Vermilion)

Tree verify: badges byte has THUNDER; HM01 and TM24 bag events; S.S.
TICKET consumed. [Tree numbering note: the tree calls the S.S. Anne
fight "rival battle 2" — it is actually the THIRD rival fight; the
Cerulean one below comes first. Cosmetic; tree text stays.]

### A. Micro-goals (DRAFT)

1. Heal, then walk north out of Cerulean toward the bridge. The RIVAL
   waits at the bridge foot: PIDGEOTTO L17 (TACKLE — birds resist
   vines), ABRA L16 (only Teleports — free kills), RATTATA L15,
   CHARMANDER L18 (TACKLE — fire resists vines). Potion below half.
   DONE: the rival is beaten (his goodbye speech happened). Budget
   30m.
2. NUGGET BRIDGE: five trainers in a row, one fight at a time, heal
   back at the Center between fights if below half (beaten trainers
   stay beaten). At the far end a sixth man gives a NUGGET and then
   attacks (he is a ROCKET) — fight him too.
   DONE: "[bag: +1 NUGGET]" and the bridge row is behind you. Budget
   45m.
3. Routes 24/25 east to BILL'S HOUSE: about ten trainers on the way;
   fight what stops you, Potion below half, and catch ONE ODDISH if
   it appears (species count). At the cottage: talk to the person
   (he is the Pokemon on the floor — mash his story), answer YES to
   help, walk to the MACHINE and press A, then talk to BILL again.
   DONE: "[bag: +1 S.S. TICKET]" happened. Budget 60m.
4. Back to Cerulean, heal. The house north of the gym was burgled
   (the door police): enter, out the smashed back wall, the ROCKET
   in the yard fights you and hands over TM28.
   DONE: "[bag: +1 TM28]" happened. Budget 30m.
5. South out of Cerulean (Route 5): the road drops over one-way
   ledges toward the gate. The Saffron gate guard is thirsty and
   turns you back — take the UNDERGROUND PATH instead: enter the
   house beside the gate, downstairs, walk the tunnel south, up and
   out onto Route 6.
   DONE: location reads Route 6. Budget 20m.
6. Route 6 south to VERMILION: a few trainers; heal at the Center.
   DONE: location reads Vermilion Pokemon Center. Budget 20m.
7. THE SHIP (it leaves forever once you walk off it — everything on
   board happens THIS visit). Board at the dock (the ticket is
   checked automatically). Inside: work toward the CAPTAIN'S room at
   the stern top floor. The RIVAL blocks the stairs up: PIDGEOTTO
   L19, RATICATE L16, KADABRA L18, CHARMELEON L20 — same answers as
   before, Potion below half. Then the Captain's room: talk, mash —
   you rub his back and he hands over HM01.
   DONE: "[bag: +1 HM01]" happened. Budget 60m.
8. Leave the ship (it sails as you step off — that is expected).
   Teach CUT: use HM01 on IVYSAUR, forget TACKLE (one deliberate
   pick — CUT replaces it as the neutral attack; label-first on the
   forget menu).
   DONE: CUT on the team line's move list. Budget 15m.
   [Checkpoint: HMs are unforgettable in Gen 1 — this is permanent
   and intended; Cut = slot 1.]
9. The gym door is behind a small TREE: stand beside it, use_cut
   (the tree vanishes), enter. Inside, the door to SURGE is locked
   by TWO switches hidden in the TRASH CANS: press A on cans; when
   one clicks, the SECOND switch is always in a can TOUCHING it —
   check each neighbor; a wrong neighbor resets BOTH (lights out,
   start over — this is normal, not a bug; say so in notes, not
   COACH). Two gym trainers may interrupt — electric vs IVYSAUR is
   half damage.
   DONE: the gate opens (both locks click). Budget 45m.
10. LT. SURGE: VOLTORB L21, PIKACHU L18, RAICHU L24 (Thunderbolt).
    IVYSAUR resists electric: VINE WHIP everything (neutral).
    Potion below half; loss protocol standard.
    DONE: badge announcement + "[bag: +1 TM24]". Budget 45m.
11. If PIKACHU is on the team: teach TM24 THUNDERBOLT to PIKACHU,
    forget GROWL (label-first on the menus).
    DONE: THUNDERBOLT on Pikachu's move list. Budget 10m.

### B. Waypoint prep (all GUESS-from-warp/object-tables — derive the
exact numbers from pret at act prep, the drill that produced the
stretch3 block)

```yaml
  # Cerulean north exit / bridge foot; Bill's house door (map 88);
  # Route 5 gate + underground house doors (maps 70/71/74); Route 6
  # gap to Vermilion; Vermilion Center/Mart/Gym doors + dock warp
  # (map 5 warp table); S.S. Anne: stairs per floor, rival spot,
  # captain's door (maps 95-101 warp tables); the gym's cut tree
  # (curated: one tile beside the gym door).
```

Mint walk_to names small: "the bridge", "Bill's house door", "the
underground house", "the dock", "the Captain's room stairs", "the
cut tree by the gym", "Lt. Surge". Prune ship waypoints the moment
the ship is left (it is gone).

### C. Data prep

- tiles.yaml NEW HARVESTS EXPECTED: underground (tunnel), SHIP,
  SHIP_PORT (dock). Pre-ingest from pret collision lists before the
  act (the unharvested-tileset = dead-walks lesson); tag any misses
  live via the raw-dump fallback.
- marts.yaml: Vermilion (91) INGESTED (fetched).
- NEW SKILL CLASS — FIELD MOVES: use_cut (goal 9) is the first
  overworld party-menu move. Wire as a minted intent (same pattern
  as use_<item>: party slot resolved at runtime from the team read,
  judge checkpoints at each screen). The same executor carries
  use_flash (Act 4), use_surf (Act 8), use_strength (Act 10) —
  build it once here, parameterized. Glue-legal: deterministic
  geometry once the intent is known.
- Savestates: pin slot 2 at the DOCK before boarding (the ship is a
  point of no return for HM01); re-pin pre-Surge.

### D. Risk brief

- SHIP DEPARTURE is the act's irreversible hazard: the HM01 bag
  event MUST exist before any goal lets the model step off. Goal 7's
  DONE is the bag event, goal 8 starts with leaving — the coach
  validates the goal-7 stamp against bag RAM before goal 8 feeds
  (this is exactly what the single-goal feed is for).
- Trash-can maze (KNOWN WEDGE, pre-marked in the tree): the
  adjacent-can drill is in goal text; expect resets; loop_detected
  may fire on the can-pressing walk pattern — it is a menu-ish false
  positive class, check before intervening. goal_overtime response:
  none needed, the reset loop is bounded by design (2^-ish odds each
  round).
- Underground path gates: the far-doorway drill (a run-wide Rules
  line) — plain walks only in gates.
- Rival fights x2: PIDGEOTTO confusion (Sand-Attack accuracy drops
  make TACKLE whiff — the model may flag COACH on repeated misses;
  answer: keep attacking, misses are the mechanic, not a wedge).
- CUT teach: first field-move skill firing — watch the judge
  checkpoint feedback like the first buy firing.
- goal_stamped anchor: badges byte THUNDER bit; HM01/TM24 bag RAM.

### E. Team/level gate

IVYSAUR L22-24 at Surge (PoisonPowder learn event at 22: LEARN,
forget GROWL — Rules carry the drill). PIKACHU with THUNDERBOLT if
present. Species ~8 (Oddish, Magikarp optional via the Old Rod house
in Vermilion — free +1, add as an optional half-goal if count lags).

---

## ACT 4 — RAINBOW badge (Erika, Celadon)

Tree verify: badges byte has RAINBOW; TM21 bag event; HM05 in bag.

### A. Micro-goals (DRAFT)

1. SPECIES CHECK (the Flash gate): the aide ahead pays out only at 10
   kinds owned. Current count is on your state line. If below 10:
   top-up catches first — the Old Rod in Vermilion (the house by the
   Center gives it free: talk, YES) catches a MAGIKARP from ANY water
   edge (+1); DIGLETT is guaranteed in the cave ahead (+1); a SANDSHREW
   sometimes shares that cave [checkpoint: verify vs pret — GUESS,
   Diglett/Dugtrio only in Red; drop the Sandshrew claim at mint].
   DONE: "You have owned 10 or more kinds" (or the catches ahead are
   listed in notes as the plan). Budget 30m.
2. DIGLETT'S CAVE: the door is east of Vermilion on Route 11's near
   side. Inside: catch ONE DIGLETT (they are everywhere), then walk
   the tunnel to its far ladder — it is one long unlit-but-visible
   corridor, no Flash needed.
   DONE: location reads Route 2 (the far exit drops there). Budget
   30m.
3. South a few steps to the gate house beside the exit; INSIDE, go
   UPSTAIRS: Oak's AIDE checks your Pokedex — at 10+ kinds he hands
   over HM05. (Gate rule as always: plain walks, far doorway.)
   DONE: "[bag: +1 HM05]" happened. Budget 15m.
4. Teach FLASH: use HM05 on PIKACHU, forget QUICK ATTACK (label-first
   on the forget menu). [If no Pikachu on the roster: catch a VOLTORB
   on Route 10 before the tunnel (goal 7 carries it) and teach Flash
   there instead — adjust at mint.]
   DONE: FLASH on a team move list. Budget 10m.
5. Return: back through Diglett's Cave to Vermilion, north through
   the Underground Path to Route 5, into Cerulean; heal; buy 3 REPELs
   at the Cerulean mart (buy_repel_x3).
   DONE: bag shows 3 REPELs, team full, location reads Cerulean.
   Budget 45m.
6. East out of Cerulean along Route 9 (a long trainer road — fight,
   Potion below half) to Route 10's Center by the tunnel mouth. Heal.
   DONE: location reads Rock Tunnel Pokemon Center, team full.
   Budget 45m.
7. ROCK TUNNEL, upper floor. At the mouth: use_repel, then use_flash
   the moment the screen goes dark (it lights the cave). Legs, each
   with a CHECK bearing [checkpoint: the exact leg bearings come from
   the OFFLINE-DERIVED walkable map — this dungeon is the plan's
   worst maze after Victory Road; do NOT send the model in on prose]:
   (a) to the first ladder down; (b) across the lower floor's west
   arm to the ladder back up; (c) the upper floor's south run to the
   final ladder; (d) lower exit corridor to daylight. Trainers are
   frequent and unavoidable; re-Repel when the first wild battle
   breaks through.
   DONE: location reads Route 10 (south side, daylight). Budget 90m.
8. South into LAVENDER TOWN; heal. The tower here is ghost-blocked —
   note it and move on (its act comes later).
   DONE: location reads Lavender Pokemon Center, team full. Budget
   15m.
9. West onto Route 8; the Saffron gate turns you back (thirsty guard
   again) — take the UNDERGROUND PATH house just south of the gate,
   tunnel west, up onto Route 7, west into CELADON. Heal.
   DONE: location reads Celadon Pokemon Center, team full. Budget
   30m.
10. CELADON ERRANDS, the department store (the tall building; floors
    by elevator or stairs):
    (a) ROOF: two vending machines. Buy TWO FRESH WATERs (¥200 each)
        [wire buy_fresh_water at prep — vending is a menu, not a
        mart clerk]. CHECK: "[bag: +1 FRESH WATER]" twice.
    (b) ROOF: the little girl beside the machines — GIVE her one
        FRESH WATER (talk, YES): she hands over TM13 (ICE BEAM — the
        run's endgame weapon; the other Fresh Water is for a
        thirsty guard later: rule-silencing "do not drink or give
        away the second one").
        CHECK: "[bag: +1 TM13]".
    (c) 4F: buy ONE THUNDERSTONE (¥2100) if money ≥¥3500.
        CHECK: "[bag: +1 THUNDERSTONE]".
    DONE: all three CHECKs in notes. Budget 45m.
11. If PIKACHU is on the team and THUNDERBOLT is on its list: use the
    THUNDERSTONE on PIKACHU — it becomes RAICHU (stronger, same
    moves). When the screen shows it changing, WAIT — never press B
    during an evolution.
    DONE: team line shows RAICHU. Budget 10m.
12. Optional (skip on overtime): the grass on Route 7 (east edge of
    town): catch ONE GROWLITHE (it appears here in Red) — it is the
    clean answer to the next gym. If 30 minutes pass without one,
    move on.
    DONE: GROWLITHE on team or in the box, or the budget expired.
    Budget 30m.
13. ERIKA's gym (south-center of town; a CUT tree may guard the door
    [checkpoint GUESS: Celadon gym's door is open, the cut tree is
    at the gym's side entrance — verify at prep; if open, drop the
    clause]): trainers inside are grass-types. ERIKA: VICTREEBEL
    L29, TANGELA L24, VILEPLUME L29. IVYSAUR takes almost nothing
    from grass moves (quarter damage) but deals little back — this
    is a patience fight: GROWLITHE's EMBER takes double on all
    three (lead it if caught); otherwise CUT for neutral damage and
    Potion through the Sleep Powders [checkpoint: Wrap from
    Victreebel + sleep spam is the slog class — the overtime answer
    is levels (L29+), not new purchases].
    DONE: badge announcement + "[bag: +1 TM21]". Budget 60m.

### B. Waypoint prep (derive exact coords from pret at act prep)

```yaml
  # Diglett's Cave doors both ends (maps 85/46/197 warp tables);
  # Route 2 gate house (49); Cerulean mart door (67); Route 9/10
  # bends as needed AFTER the offline map derivation; Rock Tunnel
  # Center door (81), tunnel mouth, per-leg ladder waypoints from
  # the derived map (maps 82 + B1F id — check constants at prep);
  # Lavender Center (141); Route 8 underground house (80), Route 7
  # exit (77); Celadon Center (133), dept store door (122), gym
  # door, Erika (object table); the Route 7 grass patch.
```

Keep the minted vocabulary small per the standing rule: tunnel legs
get "the first ladder", "the ladder back up", "the last ladder",
"daylight" — four names, pruned the moment Lavender stamps.

### C. Data prep

- OFFLINE WALKABLE DERIVATION for Rock Tunnel BOTH floors (the
  probe-tool script from Act 1 prep, run on the tunnel's block
  data). Leg waypoints and the (a)-(d) route text come from this
  derivation, marked GUESS until the first live crossing promotes
  them.
- tiles.yaml: LOBBY (dept store) + any Celadon-mansion/interior
  variants; UNDERGROUND already harvested in Act 3. Rock Tunnel is
  CAVERN (done). Verify the DARK-cave behavior: before Flash the
  screen is black — the walkable grid still reads normally from RAM
  (the harness sees through darkness; the MODEL does not — this
  asymmetry is why goal 7 orders use_flash immediately; never let
  goals route a dark screen).
- marts.yaml: Lavender (150), Celadon 2F clerk 1 (123), Celadon 4F
  stones (125) all INGESTED (fetched). Celadon two-clerk floors:
  RESOLVED by modeling only clerk 1 per floor (the yaml says so);
  the 2F TM clerk and 5F are off-plan and unminted on purpose.
- SKILLS: buy_fresh_water (vending menu, wire at prep);
  use_thunder_stone (the items.py use path with a party-slot
  target — same flow as use_potion outside battle; verify the
  target-selection cursor math handles slot 2+).
- NEW STATE CANDIDATE (decide at prep): "You are under REPEL (no
  weak wild Pokemon appear)". Serving criterion: repel's remaining
  effect is invisible on-frame and the model forgets it used one —
  BUT the bag event + notes cover it weakly. Lean NO unless tunnel
  wedges show repel confusion; note kept here for the record.
- Savestates: pin slot 2 healed at the Rock Tunnel Center pre-entry;
  re-pin pre-Erika.

### D. Risk brief

- Rock Tunnel is the act's wedge magnet: maze + darkness + Zubat
  spam. Mitigations: offline-derived legs, Flash-first ordering,
  Repels, the flee rule. Coach: loop_detected inside the tunnel →
  check the leg notes against the derived map; goal_overtime →
  re-cut the current leg into two shorter bearings from the map.
- Ghost-item class: NONE of the tunnel/route items are waypointed
  (only leg anchors) — keep it that way; every advertised bearing
  must stay reachable (the pathability lesson).
- Dept store is menu-dense: expect menu false positives; the shop
  focus trap applies at the 4F stone counter (skill checkpoints
  handle; watch the quantity render-wait on a x1 stone buy).
- The second FRESH WATER is a standing hazard: nothing stops the
  model giving both away except the rule-silencing line — coach
  checks bag RAM for it before Act 7's mint (a lost drink = a
  Celadon round trip, not a run-killer).
- Erika slog: sleep-spam turns look like stuck turns; slow_streak
  may fire mid-fight. The battle line + "About this battle" carry
  the truth; nudge text should say "asleep is a state, keep
  attacking when awake".
- goal_stamped anchor: badges RAINBOW bit; HM05/TM13/TM21 bag RAM.

### E. Team/level gate

IVYSAUR L26-29 at Erika; RAICHU if the stone landed; GROWLITHE
optional. Species comfortably 10+ (gate passed at goal 3). Cash
watch: stone + repels + waters ≈ ¥3300 — arrive from Act 3 with
≥¥4500 (Surge + S.S. Anne trainer payouts cover this; check at act
prep, cut the stone if short).

---

## ACT 5 — story gates (Rocket, ghosts, the Flute)

Tree verify: SILPH SCOPE and POKE FLUTE bag events; a Snorlax route
open (crossed it). No badge — the act ends standing south of the
Route 12 Snorlax spot.

### A. Micro-goals (DRAFT)

1. GAME CORNER (west-center Celadon): inside, a ROCKET guards the
   poster on the back wall — talk, fight, then press A on the POSTER:
   the wall opens a stairway.
   DONE: location reads Rocket Hideout B1F. Budget 30m.
2. Descend to B4F, floor by floor, one goal per floor at mint
   [checkpoint: floors B1F-B4F are maps 199-202; B2F/B3F carry the
   ARROW-TILE fields — stepping on an arrow SLIDES you until a stop
   tile; walking is not under your control mid-slide. The slide
   routes MUST come from the offline derivation (arrow directions
   are in the block data); each spin puzzle is its own micro-goal
   with the entry tile named by an adjacent landmark and the slide
   described: "step onto the arrows beside X; you will slide and
   stop; then walk N". Grunts fight on most floors.]
   DONE (per floor): location reads the next floor down. Budget
   30m per floor, 45m for each spin floor.
3. B4F: the grunt apart from the others drops the LIFT KEY when
   beaten [GUESS — verify exact holder at prep against pret scripts].
   Take the ELEVATOR (press A at its panel, choose B4F if asked) to
   the leader's hall: two grunts guard the door — fight both.
   DONE: "[bag: +1 LIFT KEY]" happened and the paired guards are
   beaten. Budget 45m.
4. GIOVANNI: ONIX L25, RHYHORN L24, KANGASKHAN L29 [GUESS levels].
   RAZOR-order: VINE WHIP takes the two rock/grounds double-or-
   quadruple; KANGASKHAN is the fight — Potion freely, it pays for
   itself. He leaves the SILPH SCOPE behind.
   DONE: "[bag: +1 SILPH SCOPE]" happened. Budget 45m.
5. Back to daylight, heal, then east to LAVENDER (Route 7 →
   underground → Route 8 — the reverse of the way in), heal again.
   DONE: location reads Lavender Pokemon Center, team full. Budget
   30m.
6. POKEMON TOWER, floors 1-2: the RIVAL waits on 2F: PIDGEOTTO ~L25,
   GYARADOS ~L22, KADABRA, CHARMELEON ~L25 [GUESS roster/levels —
   verify at prep; if RAICHU is on the team, THUNDERBOLT the
   Gyarados 4x]. Potion below half.
   DONE: the rival is beaten. Budget 30m.
7. Floors 3-6: CHANNELERs and wild GHOSTs — with the SCOPE in the
   bag the ghosts resolve to GASTLY/HAUNTER and can be fought
   normally [checkpoint: normal-type moves do NOTHING to them —
   Rules line for the act: "in the tower: never CUT/TACKLE at a
   ghost; VINE WHIP / RAZOR LEAF / EMBER / THUNDERBOLT work"].
   Catch ONE GASTLY (+1 species). On 5F there is a glowing tile
   pocket that fully heals the team — the goal names it ("the
   purified square") and routes the climb through it.
   DONE: location reads Pokemon Tower 6F. Budget 60m.
8. The 6F stairway is blocked by the MAROWAK GHOST (the mother):
   with the SCOPE it becomes a real fight (L30). No catching — it
   cannot be caught: beat it (VINE WHIP/RAZOR LEAF take double).
   DONE: the ghost is laid to rest (the way up opens). Budget 30m.
9. 7F: three ROCKETs in a row, then MR. FUJI: talk — he walks you to
   his house and hands over the POKE FLUTE.
   DONE: "[bag: +1 POKE FLUTE]" happened. Budget 45m.
10. South out of Lavender onto ROUTE 12: the sleeping SNORLAX blocks
    the road at the water's edge. Stand beside it, use the POKE
    FLUTE (use_poke_flute): it wakes ANGRY — a L30 wild battle.
    OPTIONAL CATCH (20m budget): if RAICHU knows THUNDER WAVE?
    [checkpoint: it does not by this plan's forget table — the
    catch is chip-with-CUT to red, then Poke Balls; odds are poor
    without paralysis: buy 5 GREAT BALLs in Lavender at goal 5 if
    cash ≥¥3000]. If it faints or flees, that is ACCEPTED — the
    road is what matters (a second Snorlax exists on Route 16 if
    the team ever wants one).
    DONE: the road south is open and you stand south of where it
    slept. Budget 45m.

### B. Waypoint prep

```yaml
  # Game Corner door + the poster wall (135, object table); hideout
  # per-floor ladder/lift anchors FROM THE OFFLINE DERIVATION (199-
  # 202) — spin-tile entry points named by adjacent landmarks;
  # Giovanni (object table). Tower: per-floor stair anchors (142-
  # 148), "the purified square" (5F, object/tile data), the Marowak
  # stairway (6F), Mr. Fuji (7F). Route 12 Snorlax spot (object
  # table, map 23).
```

Prune hideout waypoints when the SCOPE stamps; prune tower waypoints
when the FLUTE stamps.

### C. Data prep

- OFFLINE DERIVATION: hideout B1F-B4F including ARROW TILES (ids +
  directions from the block data — the derivation script gains an
  arrow-aware mode that renders slide endpoints; each entry tile →
  landing tile pair goes into the goal text), and tower floors
  (simple donut floors — cheap).
- tiles.yaml NEW HARVESTS: FACILITY (hideout), CEMETERY (tower).
  Pre-ingest collision lists; arrow tiles are WALKABLE in the
  collision sense — the derivation, not tiles.yaml, carries their
  behavior.
- Harness verify item: do walk macros/BFS treat arrow tiles as
  plain walkable? They will path THROUGH them and the slide will
  teleport the player off-route mid-macro. Mitigation at prep:
  either (i) goals only ever use plain single-direction walks on
  spin floors (walk_north etc. stop at the slide's end — verify
  live early on B2F), or (ii) exclude arrow tiles from BFS goals
  in navigate.py (small glue change — movement geometry, legal).
  Decide at prep; (i) needs no code.
- marts.yaml: Lavender (150) INGESTED (fetched) — Great Balls for
  goal 5's optional Snorlax buy are on its shelf.
- SKILLS: use_poke_flute (overworld item use — items.py path, works
  today; the Snorlax targeting is positional: stand adjacent).
- Savestates: pin slot 2 pre-hideout descent; re-pin pre-tower;
  re-pin pre-Snorlax (the flute battle is one-shot per Snorlax).

### D. Risk brief

- SPIN TILES are the act's novel wedge class: mid-slide, last_move
  reports impossible strides and loop_detected may fire on the
  repeated slide lap. The goal text pre-explains the slide; the
  coach expects weird stride reports on B2F/B3F and does NOT treat
  them as harness bugs (write this in the run's learnings at mint).
- Ghost-immunity trap: the model's default attack rule says CUT
  (slot 1) — in the tower that is a zero-damage loop the detectors
  cannot see (damage-free novelty). The act Rules OVERRIDE the
  default attack for the tower (yield clause in the base rule +
  act-scoped battle drill). Coach watch: any tower battle lasting
  10+ turns.
- The 5F heal square is load-bearing for the climb budget — if the
  model misses it, blackouts loop the tower. Its bearing is a
  named waypoint; the goal routes THROUGH it explicitly.
- Marowak stairway: done_goal has no bag event to anchor — the
  verify is the opened stairway (location 7F on the next goal).
  Coach validates the goal-8 stamp by the 7F transition, not the
  announcement.
- Snorlax catch tilt: bounded by budget + "accepted" wording; the
  coach does NOT extend it on a COACH flag (write the answer into
  the goal: "a fled Snorlax is not a failure").
- goal_stamped anchors: SILPH SCOPE, POKE FLUTE bag RAM; the
  Route 12 crossing (map read south of the spot).

### E. Team/level gate

VENUSAUR arrives at 32 near this act's end [checkpoint: RAZOR LEAF
learn at Ivysaur L30 FIRST — LEARN, forget VINE WHIP; then evolve;
Rules carry both]. RAICHU/GROWLITHE supporting. GASTLY on the
roster (species; never battles). SNORLAX if the catch landed —
it becomes the STRENGTH carrier and the Sabrina answer.

---

## ACT 6 — SOUL badge (Koga, Fuchsia)

Tree verify: badges byte has SOUL; HM03 + HM04 + TM06 bag events.

### A. Micro-goals (DRAFT)

1. South along Routes 12/13: board-walks over water, fence mazes on
   13 [checkpoint: the Route 13 fence weave is a known annoyance —
   offline-derive and give 2-3 leg bearings], fishermen and bird
   keepers fight you. Potion below half; RAZOR LEAF default.
   DONE: location reads Route 14. Budget 60m.
2. Routes 14/15 west into FUCHSIA CITY; heal.
   DONE: location reads Fuchsia Pokemon Center, team full. Budget
   45m.
3. SAFARI ZONE (the gate building at the top of town): pay ¥500 at
   the desk (YES to enter). Inside the rules change: no fighting —
   every wild Pokemon meets a BALL/BAIT/ROCK/RUN menu; RUN always
   works and is the act's answer ("we are here for ITEMS, not
   catches" — rule-silencing for the catch instinct + the battle
   rules). STEP LIMIT: the Safari ends itself after 500 steps and
   sends you back to the gate — the route below is measured to fit
   with margin; NO wandering, NO backtracking.
   Legs [checkpoint: from the offline derivation of the four zone
   maps — the numbers below are GUESS until then]:
   (a) Center area → the gap to Area 1 (east);
   (b) Area 1 → the north gap to Area 2;
   (c) Area 2 → the west gap to Area 3;
   (d) Area 3: the GOLD TEETH lie in the open on the way (bag
       event proof); then the SECRET HOUSE at the far corner —
       enter, talk: the man hands over HM03 (SURF).
   Each leg CHECKs its area transition in notes ("safari: a done").
   If the PA announces the game is over before the house: exit,
   re-enter (another ¥500), and run the same legs — the route
   knowledge survives.
   DONE: "[bag: +1 HM03]" AND "[bag: +1 GOLD TEETH]". Budget 60m
   (one re-entry included).
4. Leave the Safari (or ride the step-limit ejection), heal, then
   the WARDEN'S HOUSE (east side of town): give him the GOLD TEETH
   (talk, the give is automatic): he hands over HM04 (STRENGTH).
   DONE: "[bag: +1 HM04]" happened. Budget 20m.
5. Teach moves: STRENGTH to SNORLAX if present (forget nothing
   critical — its slots are free) [else HOLD HM04 for LAPRAS next
   act — note in the ledger]. SURF waits for LAPRAS (nothing on
   the roster should burn a slot on it) [checkpoint: if no Snorlax
   AND the roster has a throwaway water catch, reconsider at mint;
   default HOLD].
   DONE: the teach done or the hold noted. Budget 10m.
6. KOGA's gym (center of town): the walls inside are INVISIBLE —
   the trainers you can see stand at the maze's turning points.
   Drill: walk toward the NEXT visible trainer; when a step is
   refused, slide along the wall you just found (the can_move
   lines name which steps work — trust them over the empty-looking
   screen). Fight the four Jugglers on the way [GUESS count].
   KOGA: KOFFING L37, MUK L39, KOFFING L37, WEEZING L43 [GUESS
   levels]. Poison-vs-poison: his sludge is half against VENUSAUR;
   RAZOR LEAF is half against him — but its guaranteed criticals
   cut through [checkpoint: gen-1 Razor Leaf crit math]. WEEZING
   SELFDESTRUCTS: keep HP above half at all times near the end;
   a boom that KOs is his win condition, not yours. SNORLAX/
   RAICHU as second string.
   DONE: badge announcement + "[bag: +1 TM06]". Budget 90m.

### B. Waypoint prep

```yaml
  # Route 12/13 leg bearings from derivation; Fuchsia Center/Mart/
  # gym/warden/safari-gate doors (warp tables, maps 152-157);
  # Safari per-area gap anchors + the teeth + the house (object
  # tables, area map ids — check constants at prep); Koga (object
  # table).
```

Prune safari waypoints the moment HM03/teeth stamp.

### C. Data prep

- NO new state field for safari steps (cut 2026-07-22, user
  generic-only rule: a zone-specific counter is exactly the
  one-problem serving the criterion exists to block). The quest text
  carries the mitigation instead: the ejection is pre-explained
  ("the game ENDS ITSELF after a step count and returns you to the
  gate") so it reads as the rules working, not a teleport bug.
- OFFLINE DERIVATION: all four safari areas, with a measured
  minimal-step route Center→1→2→3→house; the leg text in goal 3
  comes from it. Also Routes 12-15's fence/board sections and
  Koga's gym INVISIBLE walls — the gym's walls are in the block
  data even though the screen hides them: the derivation gives the
  true corridor, and the goal's trainer-to-trainer drill is the
  model-facing version of it.
- tiles.yaml: safari areas share FOREST-family tilesets [GUESS —
  check constants]; gym is GYM (done); warden/house interiors are
  HOUSE (likely done by now).
- marts.yaml: Fuchsia (152) INGESTED (fetched).
- SKILLS: safari battle menu — flee_battle's corner-reset needs a
  live verify on its FIRST safari encounter (RUN sits bottom-right
  in both menus [GUESS]; if the geometry differs, hot-fix the
  skill or swap the goal to raw "press the RUN corner" one-press
  drills). Watch it like the first buy firing.
- Savestates: pin slot 2 at the safari gate pre-entry (¥ and steps
  are consumables); re-pin pre-Koga.

### D. Risk brief

- STEP LIMIT is a benign-looking hard fail: the ejection mid-route
  with no state line looks like a wedge. The steps field + the
  "re-enter and rerun the legs" clause de-fang it. Coach: if two
  ejections happen without the teeth, the route derivation is
  wrong — probe live, fix legs.
- Safari menu novelty: first encounter inside is the verify moment
  for flee_battle; a misfire throws BAIT/ROCKs (harmless) or a
  BALL (loses one of 30 — harmless this run since catches are
  off-plan).
- Invisible walls: can_move is the ONLY honest signal (the screen
  actively lies) — the goal says trust the lines; expect
  loop_detected if the model walks the same refused step; nudge
  text should quote the trainer-to-trainer drill.
- Selfdestruct/Explosion: sudden-KO turns can strand a stamped-
  feeling fight; the HP-above-half line is the whole mitigation.
- goal_stamped anchors: SOUL bit; HM03/HM04/GOLD TEETH/TM06 bag
  RAM.

### E. Team/level gate

VENUSAUR L35-38 at Koga. SNORLAX (if present) carries STRENGTH.
Species count irrelevant now (gate passed). Cash: safari fees +
restocks ≈ ¥2000 across the act — trainer-dense routes more than
cover it.

---

## ACT 7 — MARSH badge (Sabrina, Saffron)

Tree verify: badges byte has MARSH; MASTER BALL + TM46 bag events;
LAPRAS on team or in box.

PARTY-SLOT PRECONDITION (plan-side, enforced at mint): enter Silph
with FIVE or fewer on the team — the LAPRAS giver needs a free slot,
and PC box operations are NOT in the wired vocabulary (the deposit
menu sits one cursor step from RELEASE; keeping the party at five by
plan beats wiring a deposit skill under pressure). The roster math in
the ledger keeps slot 6 open from Act 6 on: Venusaur, Raichu,
Growlithe, Snorlax-or-bird, Gastly-or-filler — audit at act prep and
simply leave the last catch boxed at whatever Center caught it
[checkpoint: catches auto-box when the party is full — exploit that:
never manually deposit].

### A. Micro-goals (DRAFT)

1. Travel to SAFFRON: from Fuchsia the clean road is back east
   (Routes 15→12) then up Route 12 to Lavender, west on Route 8 to
   the Saffron gate [checkpoint: cheaper GUESS — the Celadon-side
   gate on Route 7 if the run is west; pick at mint by where Act 6
   ended]. At the gate: the guard is thirsty — GIVE the FRESH WATER
   (talk; the give is automatic). He waves you through — and every
   other Saffron gate opens too.
   DONE: location reads Saffron City. Budget 45m.
2. Heal at the Saffron Center. Errand next door: MR. PSYCHIC'S HOUSE
   (south-east block): talk to the man — he hands over TM29
   (PSYCHIC — the endgame's second weapon; HOLD it for LAPRAS).
   DONE: "[bag: +1 TM29]" happened. Budget 20m.
3. SILPH CO (the tower filling the city center): eleven floors of
   ROCKETs. The route is card-key-then-shortcut [all floor facts
   GUESS until the offline derivation at prep]:
   (a) climb the stairs to 5F: on this floor a grunt guards the
       CARD KEY (bag event proof);
   (b) down to 3F: the card key opens the locked door to a
       TELEPORT PAD ROOM; the pad jumps straight to 7F;
   (c) 7F: the RIVAL blocks the way (PIDGEOT ~L37, GYARADOS,
       GROWLITHE?, KADABRA/ALAKAZAM, CHARIZARD ~L40 [GUESS
       roster]) — RAICHU for the bird and the fish, VENUSAUR
       holds the rest;
   (d) 7F: the cornered EMPLOYEE gives LAPRAS (YES to take it —
       the free slot is why the party is five);
   (e) pads/stairs to 11F: two guards, then GIOVANNI (NIDORINO,
       KANGASKHAN, RHYHORN, NIDOQUEEN ~L37-41 [GUESS]): RAZOR
       LEAF the rock/grounds, wear the rest;
   (f) the PRESIDENT's thank-you: MASTER BALL (NEVER use it — it
       is a trophy this run; rule-silencing in the act Rules:
       "no goal ever says throw the MASTER BALL").
   One goal per lettered leg at mint; each with its bag-event or
   floor-read CHECK; teleport pads are named waypoints ("the pad
   room on 3F") — the pad hop is a warp, the model just walks on.
   DONE (act-level): CARD KEY, LAPRAS (team/box read), MASTER BALL
   all verified. Budget 3h across the legs.
4. Teach LAPRAS its kit (it arrives ~L15 and CANNOT fight yet —
   that is expected and said out loud in the goal): TM13 ICE BEAM,
   TM29 PSYCHIC, HM03 SURF [checkpoint: order matters — teach over
   the weakest natural moves; label-first per menu. If HM04 is
   still unassigned (no Snorlax), STRENGTH goes to Lapras too —
   it takes all four].
   DONE: the team line shows LAPRAS with ICE BEAM, PSYCHIC, SURF.
   Budget 20m.
5. LAPRAS GRIND (the plan's one deliberate grind): Lapras must
   reach ~L30 before Cinnabar and the gym circuit ahead. Lead it
   into every trainer fight on the way OUT of Saffron and swap to
   Venusaur when it dips below half [checkpoint: gen-1 splits XP
   to participants — a lead-and-switch pattern is one extra menu
   per fight; the goals for Acts 8-9 carry "LAPRAS leads" lines
   instead of a dedicated grind camp; this goal just sets the
   habit on Saffron's dojo next door: the FIGHTING DOJO's five
   trainers are optional XP with a free HITMONLEE/CHAN at the end
   (either; label-first) — take the fights, skip nothing].
   DONE: the dojo is cleared (the gift fight offer appeared —
   pick either, one press). Budget 60m.
6. SABRINA's gym: a 3x3 grid of rooms linked ONLY by teleport
   pads. The pad route to her is fixed — legs from the derivation
   [GUESS until prep]: each goal names "step on the pad in the
   <corner> of this room", CHECK = the room read changes. Optional
   trainers are skippable by route. SABRINA: KADABRA L38, MR.
   MIME L37, VENOMOTH L38, ALAKAZAM L43. VENUSAUR STAYS BACK
   (psychic takes it double) — LAPRAS leads: ICE BEAM/PSYCHIC
   (VENOMOTH takes PSYCHIC double); SNORLAX bodies ALAKAZAM if
   present (it is paper-thin physically); RAICHU cleans.
   DONE: badge announcement + "[bag: +1 TM46]". Budget 90m.

### B. Waypoint prep

```yaml
  # Saffron gate (Route 8 or 7 side), Center door, Mr. Psychic's
  # house (183), dojo (177), Silph door (181); per-floor stair/pad
  # anchors FROM DERIVATION (2F-11F map ids from constants at
  # prep); Sabrina's gym pad-route anchors (178); Sabrina (object
  # table).
```

Prune Silph anchors when the MASTER BALL stamps.

### C. Data prep

- OFFLINE DERIVATION: Silph 2F-11F (stairs, locked doors, pads —
  pads are warp-table entries, fully derivable) → produces the
  lettered route in goal 3 with VERIFIED pad pairs; same for
  Sabrina's pad grid. This is the derivation tool's biggest test —
  schedule real time for it at act prep.
- tiles.yaml: FACILITY already harvested (hideout); Silph shares it
  [GUESS — verify]; INTERIOR variants for the dojo.
- marts.yaml: Saffron (180) INGESTED (fetched).
- SKILLS: none new — pads are walk-on warps; the Lapras take and
  the drink give are conversations (choice-stop guard).
- Savestates: pin slot 2 pre-Silph (Lapras/Master Ball are one-
  shots); re-pin pre-Sabrina.

### D. Risk brief

- The FRESH WATER must still be in the bag (Act 4 risk carried
  forward) — coach checks bag RAM BEFORE minting goal 1; if it is
  gone, prepend a Celadon vending round trip.
- Silph is eleven floors of the same wedge classes (mazes, pads,
  grunts) — the derivation is the whole defense; goal_overtime on
  any leg → re-derive that floor live (probe), never prose-guess.
- Party-slot precondition: coach verifies party count == 5 before
  the Lapras leg feeds; if 6, the goal says which catch to leave
  boxed — NO deposit flow exists on purpose.
- Lapras teaching session is menu-dense with three irreversible
  forget prompts back to back — each TM is its own sub-goal CHECK
  in notes; label-first every screen.
- Sabrina's Alakazam can sweep at L43 — the goal pre-authorizes
  feeding it Full Restores? NO (off-list buys banned): the answer
  is SNORLAX/level gates; if the fight is lost twice, the coach
  gates on Lapras L35 + dojo/route grinding, not purchases.
- goal_stamped anchors: MARSH bit; CARD KEY/LAPRAS(party or box
  RAM)/MASTER BALL/TM29/TM46 bag RAM.

### E. Team/level gate

VENUSAUR L38-42; LAPRAS L15→~30 (the grind debt starts here — it
must not lead real fights until ~25); RAICHU, GROWLITHE, SNORLAX/
HITMON as the fifth. Slot 6 = Lapras.

---

## ACT 8 — VOLCANO badge (Blaine, Cinnabar)

Tree verify: badges byte has VOLCANO; TM38 bag event.

### A. Micro-goals (DRAFT)

1. Travel Saffron → Fuchsia (the Act 7 route reversed; LAPRAS
   leads every trainer fight that offers, swap out below half).
   Heal at Fuchsia.
   DONE: location reads Fuchsia Pokemon Center, team full. Budget
   45m.
2. South through the town's bottom onto ROUTE 19: at the water's
   edge, use_surf (LAPRAS carries you — the world's water is now
   a road). SWIMMERs float in the channel and fight like any
   trainer. South, then west onto ROUTE 20.
   DONE: location reads Route 20. Budget 45m.
3. Route 20 west past the SEAFOAM ISLANDS (two cave mouths on the
   way — do NOT enter either [checkpoint: crossing the islands'
   beach is the normal route; the dungeon is skippable in Red —
   GUESS verify at prep that the surf line continues past without
   entering]; the islands' articuno is out of scope). More
   swimmers; LAPRAS leads.
   DONE: location reads Cinnabar Island. Budget 60m.
4. Heal at the Cinnabar Center; restock at the mart (HYPER/SUPER
   POTIONs to 6, 2 FULL HEALs — both on the ingested shelf).
   DONE: team full, restock events in the bag. Budget 20m.
5. POKEMON MANSION (the ruined building west of town): doors are
   locked or opened by STATUE SWITCHES — press A on the glowing
   statues; each press toggles doors somewhere on the floor. The
   route to the basement key [GUESS until derivation]: 1F east
   stairway up → 2F-3F over the balcony hole down → 1F pit to
   B1F → the SECRET KEY on its table (bag event proof). Wild
   GRIMER/KOFFING/GROWLITHE here; scientists and burglars fight.
   One goal per floor-leg at mint, statue presses named by
   adjacent landmarks.
   DONE: "[bag: +1 SECRET KEY]" happened. Budget 90m.
6. Escape the mansion (walk out or ESCAPE ROPE if carried), heal,
   then the GYM (its door needs the SECRET KEY — it unlocks by
   itself at the door). Inside: QUIZ MACHINES gate each room —
   press A, read the question, answer YES or NO (the ANSWERS, in
   room order, go in the goal text verbatim at mint [checkpoint:
   pull from a walkthrough at prep — they are fixed]; a WRONG
   answer opens a trainer fight instead — that is a fallback,
   not a failure: win it and the door opens anyway).
   DONE: the last quiz door is open (Blaine visible). Budget 45m.
7. BLAINE: GROWLITHE L42, PONYTA L40, RAPIDASH L42, ARCANINE L47
   (Fire Blast). This is LAPRAS's gym: SURF takes everything
   double; keep VENUSAUR benched (fire takes it double). FULL
   HEAL a burn if it lands on Lapras [checkpoint: gen-1 burn
   halves attack — Surf is special, the burn is cosmetic; drop
   the line at mint if it reads as noise].
   DONE: badge announcement + "[bag: +1 TM38]". Budget 45m.

### B. Waypoint prep

```yaml
  # Fuchsia south shore surf-entry tile (curated); Route 20 cave
  # mouths (to AVOID — waypoint them as "do not enter" comments
  # only if the surf line needs a steering anchor); Cinnabar
  # Center/Mart/Mansion/Gym doors (warp tables, maps 165/166/
  # 171/172); mansion per-floor stair/pit anchors FROM DERIVATION
  # + statue positions (object/tile data); Blaine (object table).
```

### C. Data prep

- SURF SUPPORT — the act's real work, schedule it BEFORE the act:
  (a) tiles.yaml: water tile ids per tileset gain a `surfable:`
      list (they stay non-walkable on foot);
  (b) navigate.py/BFS: when the surf flag RAM says riding, water
      is walkable ground; dismount = stepping onto land (the
      game handles it);
  (c) use_surf minted intent: face water + A + YES (the field-
      move executor from Act 3 carries it);
  (d) state_lines: "You are SURFING on the water." (serving
      criterion: the riding state changes which steps work and
      the sprite is easy to misread — PASS; add provider with
      docstring).
  Verify the whole chain live on the Fuchsia shore BEFORE minting
  goal 2's crossing (a 10-minute supervised test beats a wedged
  night — the 0x55 class: behavioral claims get live eyes).
- OFFLINE DERIVATION: mansion floors (statue-toggle doors make
  walkability DYNAMIC — derive both toggle states; the goal text
  carries the working sequence); gym room chain is linear (no
  derivation needed beyond door order).
- tiles.yaml: MANSION tileset harvest; Seafoam exterior is
  overworld (done).
- marts.yaml: Cinnabar (172) INGESTED (fetched).
- Quiz answers: pull the fixed YES/NO list from a walkthrough at
  prep (walkthrough facts may go in goals text verbatim; they are
  behavior-free).
- Savestates: pin slot 2 before the first surf tile (new movement
  mode); re-pin pre-mansion and pre-Blaine.

### D. Risk brief

- SURF is a new movement mode for every layer at once (model,
  macros, detectors): expect nav_ineffective noise at the
  water's edge and treat the first crossing as a supervised
  shakeout (coach watches live, not by alarm).
- Mansion statues: dynamic doors invalidate the static derivation
  if a statue press goes uncounted — each leg's CHECK names the
  door state it expects ("the way north stands open"); two failed
  legs → live probe (probe-after-two).
- Wild MUK/GRIMER poison spam: FULL HEALs bought in goal 4;
  antidote rule carries.
- Blaine loss loop: blackout returns to the Cinnabar Center
  (cheap retry); two losses → Lapras level gate (L35+) via Route
  21 swimmers south of town.
- goal_stamped anchors: VOLCANO bit; SECRET KEY/TM38 bag RAM.

### E. Team/level gate

LAPRAS L30-35 carrying the gym; VENUSAUR L40-44 benched for it.
RAZOR LEAF Venusaur + SURF/ICE BEAM/PSYCHIC Lapras is now the
run's core damage; RAICHU for birds/water.

---

## ACT 9 — EARTH badge (Giovanni, Viridian)

Tree verify: badges byte has all 8; TM27 bag event.

### A. Micro-goals (DRAFT)

1. Surf ROUTE 21 north (swimmers + tangela grass on the strip),
   land at PALLET TOWN — the journey's first map, eight badges
   later. Heal at home is not a thing: walk Route 1 north to
   VIRIDIAN, heal there.
   DONE: location reads Viridian Pokemon Center, team full.
   Budget 60m.
2. The GYM beside the city's west road is OPEN now (it was locked
   in Act 0). Inside: arrow SPIN TILES again (the hideout drill
   verbatim: step on the named arrows, slide, then walk) plus the
   toughest gym trainers yet [checkpoint: derivation at prep;
   the spin route to Giovanni is short if the legs are right].
   DONE: the way to GIOVANNI stands open (his bearing 2 tiles or
   less). Budget 60m.
3. GIOVANNI, round three: RHYHORN, DUGTRIO, NIDOQUEEN, NIDOKING,
   RHYDON ~L42-50 [GUESS levels]. VENUSAUR's gym: RAZOR LEAF
   takes RHYHORN/RHYDON quadruple and DUGTRIO double; LAPRAS
   SURF/ICE BEAM covers the Nido pair (ground takes both
   double). His EARTHQUAKE cannot touch... [checkpoint: nothing
   on our team flies — the line is wrong, cut it; the real note:
   FISSURE one-hit-KOs on a hit — keep HP irrelevant, it either
   misses or KOs; revive nothing, swap and continue].
   DONE: badge announcement + "[bag: +1 TM27]". Budget 60m.

### B. Waypoint prep

```yaml
  # Route 21 surf-line anchors if the strip needs steering;
  # Viridian Gym door (map 1 warp table — the Act 0 file kept
  # Viridian's doors for exactly this return); gym spin-tile
  # entry anchors FROM DERIVATION (45); Giovanni (object table).
```

### C. Data prep

- OFFLINE DERIVATION: Viridian Gym spin tiles (the hideout
  arrow-aware mode reused).
- Everything else is revisited ground — verify the Act 0
  Viridian waypoints survived in the live file (the standing
  keep-it-small rule kept the doors).
- Savestates: re-pin pre-gym.

### D. Risk brief

- Spin tiles round two — the Act 5 learnings entry (weird stride
  reports are expected, not bugs) carries over verbatim.
- FISSURE turns look like instant losses; the goal pre-explains
  (swap and continue). A blackout here is a Viridian Center
  respawn — the cheapest loss loop in the game.
- goal_stamped anchor: badges byte == all 8 (0xFF).

### E. Team/level gate

VENUSAUR L43-46, LAPRAS L38-42, RAICHU L35+, the bench filled by
SNORLAX/HITMON/GROWLITHE. TM ledger check before Act 10: ICE BEAM
and PSYCHIC on Lapras, THUNDERBOLT on Raichu — the E4 kit is
complete; nothing new is coming.

---

## ACT 10 — the end

Tree verify: Hall of Fame (credits; post-champion save state).

### A. Micro-goals (DRAFT)

1. West from Viridian onto ROUTE 22; the RIVAL waits at the rise
   before the gate: PIDGEOT ~L47, RHYHORN, EXEGGCUTE?, GYARADOS,
   ALAKAZAM, CHARIZARD ~L53 [GUESS roster — verify at prep].
   THUNDERBOLT the birds and the fish, RAZOR LEAF the Rhyhorn,
   ICE BEAM the rest; Potion freely.
   DONE: the rival is beaten. Budget 45m.
2. ROUTE 23: the badge-check gates wave all eight through, one
   guard at a time (mash speech); grass and water legs between
   [checkpoint: one surf strip mid-route — GUESS verify].
   DONE: location reads Victory Road 1F (the cave door at the
   route's top). Budget 45m.
3. VICTORY ROAD, one puzzle per goal [legs from derivation at
   prep — the tree pre-marks this as the game's worst navigation]:
   each floor gates on a STRENGTH BOULDER pushed onto a SWITCH:
   use_strength once on arriving (it lasts the map), then the
   goal names the boulder's landmark, the pushing direction as
   cardinal steps ("stand WEST of it, walk EAST four times — the
   boulder slides ahead of you"), and the switch CHECK ("the door
   in the north wall stands open"). MOLTRES lives on a ledge
   mid-cave: do not approach the giant bird; flee if it fights
   [checkpoint: it is stationary — route around; GUESS floor].
   DONE (per floor): the next floor's read; (final) location
   reads Indigo Plateau. Budget 60m per floor, 3 floors.
4. INDIGO PLATEAU lobby: heal, then SHOP — the final list, in
   priority order, skipping what money cannot cover: 6 FULL
   RESTOREs, 4 REVIVEs, 4 MAX POTIONs (the ingested lobby shelf
   carries all three). Sell the NUGGET here only if cash is short
   [checkpoint: selling is an unwired menu path — if cash math at
   prep says the Nugget is unnecessary, DROP the sell and keep the
   vocabulary closed].
   DONE: the restore stock reads in the bag; team full. Budget
   30m.
5. THE ELITE FOUR — five fights in a row, NO Center between; the
   lobby doors lock behind you; a blackout restarts the gauntlet
   (and that is the loss loop: heal, restock, walk back in). One
   goal per member, each with a per-Pokemon script [levels GUESS
   — verify at prep]:
   (a) LORELEI (ice): DEWGONG/CLOYSTER/SLOWBRO/LAPRAS — RAICHU
       THUNDERBOLT sweeps the water; JYNX takes nothing special —
       SNORLAX/body her. VENUSAUR stays benched (ice doubles).
       Full Restore below a third, always.
   (b) BRUNO (fighting/rock): the ONIX pair take RAZOR LEAF
       quadruple; the HITMONs and MACHAMP take LAPRAS PSYCHIC
       double.
   (c) AGATHA (ghost/poison): PSYCHIC doubles on every one of
       hers (all part poison); never a normal-type move at the
       GENGARs (immune). Sleep/confusion spam: FULL HEAL early,
       not late.
   (d) LANCE (dragons): GYARADOS takes THUNDERBOLT quadruple;
       the DRAGONAIRs take ICE BEAM double; AERODACTYL takes
       THUNDERBOLT double; DRAGONITE takes ICE BEAM quadruple.
       His HYPER BEAMs KO from health — Full Restore at half,
       no lower.
   (e) THE CHAMPION — the rival's last stand: PIDGEOT L61,
       ALAKAZAM, RHYDON, EXEGGUTOR, GYARADOS, CHARIZARD L65
       [GUESS variant for our starter — verify]. The kit
       answers: THUNDERBOLT (Pidgeot/Gyarados), RAZOR LEAF
       (Rhydon), ICE BEAM (Exeggutor/Charizard... [checkpoint:
       Surf doubles Charizard too — either]), LAPRAS holds the
       middle, VENUSAUR closes.
   DONE (act and game): the Hall of Fame scene — credits roll.
   Budget 45m per member; the whole gauntlet re-runs on a
   blackout.
6. POST-CREDITS: the game returns to the title. STOP — do not
   press through into a new game [checkpoint: the ratchet's
   auto-save discipline plus a final pinned savestate at the
   Hall of Fame is the run's archival close; harness stop is a
   user/checkpoint action, not a goal].
   DONE: the run is over. The checkpoint marks the tree root [x].

### B. Waypoint prep

```yaml
  # Route 22/23 leg anchors (gates are linear); Victory Road
  # boulder/switch/ladder anchors per floor FROM DERIVATION
  # (108/194/198 + arrow-aware boulder sim if feasible — else
  # walkthrough push sequences transcribed as cardinal drills,
  # GUESS-marked); lobby doors (174); E4 rooms are linear warps.
```

### C. Data prep

- OFFLINE DERIVATION: Victory Road floors with boulder/switch
  positions (object + block data). Boulder PUSHING is plain
  walking into the boulder with Strength active — no new skill;
  the derivation must confirm each push lane has no side-slip
  tiles [checkpoint: gen-1 boulders move one tile per push,
  straight only — the lane just needs to be clear].
- use_strength: the Act 3 field-move executor's last variant —
  verify once on the first boulder.
- marts.yaml: Indigo lobby (174) INGESTED (fetched).
- E4/champion rosters + quiz-style facts: walkthrough pull at
  prep; levels into goal text as plain claims ("about level
  55") — never as certainties.
- Savestates: pin slot 2 in the lobby, healed, stocked, BEFORE
  the first door — the gauntlet's restart point; re-pin at the
  Hall of Fame (the archival state). The E4 run is the one
  stretch where the ratchet interval should tighten if the
  profile allows [checkpoint: profile knob, decide at prep].

### D. Risk brief

- The gauntlet structure (no heals, restart-on-loss) is the
  endgame risk: the answer is the shopping goal + per-member
  scripts + the lobby pin. Coach on a blackout: verify money
  RAM (halved), re-mint the shop goal with the smaller purse,
  and lower nothing else — repetition with intact knowledge is
  the design.
- Boulder mis-push CAN wedge a switch room [checkpoint: gen-1
  Victory Road boulders reset on map re-entry — leaving and
  re-entering the floor is the un-wedge; put it IN the goal
  text].
- Moltres aggro is a mis-walk away; its tile is a named
  KEEP-AWAY in the goal ("the giant bird's ledge — never step
  toward it").
- Champion variance: if the roster GUESS is wrong at contact,
  the coach hot-edits mid-gauntlet from the live battle line
  (the "About this battle" verdicts carry the type math either
  way — the scripts are conveniences, not load-bearing).
- goal_stamped anchor: the Hall of Fame flag/scene; the
  post-champion save.

### E. Team/level gate

L47-53 across VENUSAUR/LAPRAS/RAICHU + bench. If the gauntlet
gates twice on levels, the grind loop is Victory Road trainers
(they re... [checkpoint: trainers do NOT respawn — the grind
loop is wild Victory Road/Route 23 encounters; slower, but the
E4 themselves pay XP on each attempt]).

---

## Cross-cutting ledgers (checkpoint-kept, expanded from the tree)

### Team plan and the forget table

Core: BULBASAUR → IVYSAUR (16) → VENUSAUR (32).
Move-slot script (keeps attack_N mappings predictable; every learn
event pre-answered in the acts' Rules):

| Level | Event | Answer | Slots after |
|---|---|---|---|
| 7  | Leech Seed | learn (free slot) | Tackle/Growl/LeechSeed |
| 13 | Vine Whip | learn (free slot) | +VineWhip (slot 4) |
| 16 | evolve Ivysaur | WAIT through the scene (no B) | — |
| 22 | PoisonPowder | learn, forget GROWL | Tackle/PoisonPowder/LeechSeed/VineWhip |
| ~Act 3 | HM01 CUT | teach, forget TACKLE (permanent) | Cut/PoisonPowder/LeechSeed/VineWhip |
| 30 | Razor Leaf | learn, forget VINE WHIP | Cut/PoisonPowder/LeechSeed/RazorLeaf |
| 32 | evolve Venusaur | WAIT through the scene | — |
| 43 | Growth | DO NOT learn (one press B... [verify prompt shape]) | unchanged |
| 55 | Sleep Powder | learn, forget POISONPOWDER (if the run gets there) | +SleepPowder |

PIKACHU (forest, Act 1; the run's electric): Thundershock native;
TM24 THUNDERBOLT (Act 3, forget GROWL); HM05 FLASH (Act 4, forget
QUICK ATTACK); THUNDERSTONE → RAICHU (Act 4, after Thunderbolt).
Fallback if never caught: VOLTORB (Route 10, Act 4) carries FLASH;
the Thunderbolt role goes unfilled — E4 scripts lean harder on
Lapras (note the deviation in the tree when it happens).

LAPRAS (Silph 7F gift, Act 7; the run's second carry): TM13 ICE
BEAM + TM29 PSYCHIC + HM03 SURF (+HM04 STRENGTH if no Snorlax).
Arrives L15 — the grind debt (lead-and-switch from Act 7 on) is
the plan's one deliberate grind; gates: L30 by Blaine, L38+ by
the E4.

GROWLITHE (Route 7/8, Act 4, optional): the Erika/fire answer;
EMBER native at wild levels. Never a priority past Act 4.

SNORLAX (Route 12 flute battle, Act 5, optional catch): STRENGTH
carrier, Sabrina/Lorelei body answer. A miss is accepted; Route
16's twin is the backup if the team wants one later.

A BIRD (Pidgey, Act 0): roster filler and species count only —
the tree's "bird (early)" slot never became a carry in this
plan; FLY is skipped (no HM02 detour — travel is walked/surfed).
Revisit only if a wedge makes Fly worth the Route 16 side trip.

Party-slot discipline: five on the team from Act 6 until the
Lapras take (Act 7) — catches auto-box when full; never a manual
deposit (no PC flow in the vocabulary, RELEASE risk).

### HM ledger

| HM | Source (act) | Learner | Taught when |
|---|---|---|---|
| CUT (01) | S.S. Anne captain (3) | Ivysaur (forget Tackle) | Act 3, before the gym |
| FLASH (05) | Route 2 aide, 10 owned (4) | Pikachu (forget Quick Attack) / Voltorb fallback | Act 4, before Rock Tunnel |
| SURF (03) | Safari secret house (6) | LAPRAS (held until Act 7) | Act 7 teach session |
| STRENGTH (04) | Warden for Gold Teeth (6) | Snorlax, else Lapras | Act 6 or 7; needed Act 10 |
| FLY (02) | skipped | — | — |

### Key items ledger

S.S. TICKET (Bill, Act 3 — consumed boarding), OAK'S PARCEL (Act
0, consumed), SILPH SCOPE (Giovanni 1, Act 5), POKE FLUTE (Fuji,
Act 5), GOLD TEETH (Safari, Act 6 — consumed at the warden), CARD
KEY (Silph 5F, Act 7), MASTER BALL (president, Act 7 — NEVER
thrown; trophy), SECRET KEY (mansion, Act 8), NUGGET (bridge, Act
3 — emergency cash, sell only if the Act 10 shop math demands).

### Species-count ledger (the Flash gate)

Planned line to 10 owned before Rock Tunnel: Bulbasaur 1, Pidgey
2, Rattata 3, Nidoran 4 (Act 0); Pikachu 5, Weedle/Caterpie 6
(Act 1); Zubat 7, Paras 8 (Act 2); Oddish 9 (Act 3); Diglett 10
(+Magikarp free via Old Rod) (Act 4). Two-deep slack on every
step; the owned-kinds state line makes the count checkable at
every decision.

### Money ledger (floors, not budgets)

Start ¥3000. Floors the coach enforces at each act close (below
floor → insert an earn/skip step at the next mint): after Act 0
≥¥1500; Act 1 ≥¥600 post-Potions (Brock pays ~¥1400); Act 2-3
self-funding (trainer-dense); Act 4 needs ≥¥3500 at Celadon
(stone + waters + repels — cut the stone if short); Act 5-9
self-funding; Act 10 needs the E4 shop (~¥25k — gym payouts +
two acts of trainers normally land ≥¥30k; the Nugget is the
buffer). Blackouts HALVE cash — after any blackout, re-check the
current act's floor before proceeding.

### Savestate pinning protocol (slot 2; slot 1 stays the ratchet)

Starter validated (Act 0) → healed-pre-gym each badge act → cave
mouths (Mt Moon, Rock Tunnel, mansion) → the dock pre-ship (3) →
pre-hideout/pre-tower/pre-Snorlax (5) → safari gate (6) →
pre-Silph (7) → first surf tile (8) → E4 lobby stocked (10) →
Hall of Fame (archival). Loadstate policy unchanged: crash/
catastrophe recovery only — in-game blackout is the loss path
(benchmark honesty); the ONE pre-authorized rollback is a wrong
starter.

### Rival battle schedule (correcting the tree's count)

1 Oak's lab (Act 0) · [optional Route 22 early — skipped unless
met] · 2 Cerulean bridge foot (Act 3) · 3 S.S. Anne (Act 3) · 4
Pokemon Tower 2F (Act 5) · 5 Silph 7F (Act 7) · 6 Route 22 rise
(Act 10) · 7 CHAMPION (Act 10). The tree's "rival battle 2/3/4"
labels under-count by one from Cerulean on; tree text stays (its
player lines never name the count).

