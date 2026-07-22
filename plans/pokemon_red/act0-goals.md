# ACT 0 goals.md — paste-ready at run creation (Bulbasaur run)

CHECKPOINT INSTRUCTIONS (everything above the PASTE line is
checkpoint-voice; the model never sees it):
- Copy everything between the PASTE markers into
  runs/pokemon_red/<run-id>/goals.md at run creation.
- Copy the waypoints appendix into the run's waypoints.yaml.
- Do the Act 0 data prep from master-plan.md FIRST (owned-kinds state
  field; use_poke_ball battle-path watch item).
- VERIFY THE PUBLISH after the paste (the standing instruction).
- Vocabulary audited against maps.yaml renderings and the state-line
  sentences 2026-07-22; if state_lines change before launch, re-audit.
- Validation anchors for this act's goal_stamped alarms: goal 4 =
  party species RAM (BULBASAUR and nothing else — a wrong species
  here is the ONE pre-authorized loadstate rollback); goal 7/8 =
  parcel bag events; goal 8 = Pokedex owned flag; goals 10/11 =
  Pokedex owned count; act close = the tree's Act 0 verify line.

--- PASTE FROM HERE ---

# Goals

THE ROAD TO THE END (why your current goal matters):
- Beat the game = defeat the Elite Four at Indigo Plateau.
  - That needs ALL 8 GYM BADGES; the road runs through these stages:
    0. Start the journey - choose BULBASAUR and finish Oak's errand
       <- YOU ARE HERE
    1. Win the BOULDER badge from Brock in Pewter City
    2. Cross Mt. Moon and win the CASCADE badge from Misty in
       Cerulean City
    3. Meet Bill, sail the S.S. Anne, and win the THUNDER badge from
       Lt. Surge in Vermilion City
    4. Reach Celadon City through Rock Tunnel and win the RAINBOW
       badge from Erika
    5. Drive Team Rocket from Celadon, lay the Pokemon Tower ghost to
       rest, and wake the sleeping Snorlax
    6. Reach Fuchsia City, learn to SURF at the Safari Zone, and win
       the SOUL badge from Koga
    7. Free Silph Co. from Team Rocket and win the MARSH badge from
       Sabrina in Saffron City
    8. Surf to Cinnabar Island, unlock the Mansion, and win the
       VOLCANO badge from Blaine
    9. Win the EARTH badge from Giovanni in Viridian City
    10. Cross Victory Road and defeat the Elite Four.
Your current goal is one small step on this road. Unsure about it in
ANY way - looks done, looks impossible, or you just do not know what
to do? Put "COACH: <what and why>" in your notes. The coach is alerted
at once and makes the hard calls; flagging is always the right move.

1. Start a BRAND-NEW game. This cartridge has no saved game: on the
   title screen pick NEW GAME (the usual CONTINUE rule does not apply
   - there is nothing to continue). Mash through the professor's
   welcome speech. At the NAME screen: press DOWN once, then A - that
   takes the first ready-made name. If a screen full of letters opens
   anyway: press_A, then press_START, then press_A escapes it. The
   same happens once more for the other boy's name. DONE when your
   location reads Red's House 2F: mark it done then.
   Time budget: 15 minutes.

2. Go downstairs and outside. The stairs work by walking onto them;
   the front door is at the bottom of the house. DONE when your
   location reads Pallet Town: mark it done then.
   Time budget: 5 minutes.

3. Walk NORTH toward the tall grass at the top edge of town. An old
   man will stop you himself and walk you to his lab - that is the
   plan, let him; mash through everything he says. You never reach
   the grass and that is correct. DONE when your location reads
   Professor Oak's lab: mark it done then.
   Time budget: 10 minutes.

4. Choose BULBASAUR - read before you touch. Three Poke Balls sit on
   the table. At each ball: press A once and READ the words - the
   screen names which Pokemon it is. Three sub-goals; keep progress
   in your notes ("4: ball 1 was CHARMANDER, trying next") and fix
   the notes when the screen disagrees.
   (a) Read a ball's label.
       Check: the dialogue names a Pokemon.
   (b) If it names BULBASAUR: answer YES with ONE press. If it names
       anything else: answer NO with ONE press of B and read the
       next ball. Never confirm a ball you have not read.
       Check: the team line shows BULBASAUR.
   (c) The nickname question: answer NO (one press B).
   DONE when your team line shows BULBASAUR: mark it done then.
   Time budget: 15 minutes.

5. Beat the rival boy's CHARMANDER (he attacks you before you can
   leave). Use attack_1 (TACKLE) every turn; when he uses GROWL
   nothing bad happens, keep attacking. If you lose you only lose
   some money - carry on either way. DONE when the battle is over
   and your location still reads Professor Oak's lab: mark it done
   then.
   Time budget: 15 minutes.

6. Walk to Viridian City: leave the lab (south over the mats), walk
   north out of town onto Route 1 (the gap in the top edge, near the
   grass), then north the whole length of Route 1. Wild PIDGEY and
   RATTATA live in the grass: fight them with TACKLE for experience
   or flee_battle - either is fine; you have no Poke Balls yet, so
   never try to catch. DONE when your location reads Viridian City:
   mark it done then.
   Time budget: 20 minutes.

7. Get the parcel: enter the Viridian Poke Mart (the "Viridian Mart
   door" bearing), walk to the counter and talk - the clerk hands
   you a parcel for Professor Oak without being asked. DONE when
   "[bag: +1 OAK's PARCEL]" happened: mark it done then.
   Time budget: 10 minutes.

8. Deliver it: walk back south to Pallet Town (Route 1 south - the
   little ledges hop DOWN only; hopping down is a shortcut, never
   try to climb one), enter the lab, talk to Professor Oak and mash
   through the scene - he takes the parcel, and both boys receive a
   POKEDEX. DONE when "[bag: -1 OAK's PARCEL]" happened and the
   POKEDEX scene played: mark it done then.
   Time budget: 20 minutes.

9. Shop: return north to Viridian City and buy at the Mart:
   buy_poke_ball_x5, then buy_antidote_x3. Every "[bag: +N ...]"
   event is the proof. This shelf sells no POTIONs - Potion rules do
   not apply until Pewter City. DONE when the bag shows 5 POKE BALLs
   and 3 ANTIDOTEs: mark it done then.
   Time budget: 15 minutes.

10. Catch your first Pokemon in the Route 1 grass (south gap of
    town): fight a PIDGEY or RATTATA down to yellow or red HP with
    TACKLE, then use_poke_ball. If the ball misses, hit once more
    and throw again. Catch one PIDGEY and one RATTATA. Poke Balls
    only work on WILD Pokemon. DONE when your state line says you
    have owned 3 or more kinds of Pokemon: mark it done then.
    Time budget: 30 minutes.

11. Catch a NIDORAN on Route 22: the road WEST out of Viridian (the
    "gap to Route 22" bearing). Same drill: weaken with TACKLE,
    use_poke_ball. Either kind of NIDORAN counts. If the rival boy
    appears and demands a fight: fight him with TACKLE - a loss
    costs money only. DONE when your state line says you have owned
    4 or more kinds of Pokemon: mark it done then.
    Time budget: 30 minutes.

12. Heal at the Viridian Pokemon Center (the "Viridian Center door"
    bearing): walk to the counter, answer the nurse's question with
    ONE press A, mash through the rest. Then stay near the Center -
    new goals arrive next. DONE when your team is at full HP and
    your location reads Viridian Pokemon Center: mark it done then.
    Time budget: 10 minutes.

Rules (the FIRST rule that fits the screen wins - run it and stop
thinking; the current goal's own text outranks this list; a rule you
cannot follow right now does not apply - skip it without discussion):
- A fight the current goal does not say how to handle: attack_1
  (TACKLE). When the goal names a battle drill, that drill IS the
  answer - use it without comparing.
- Poke Balls only work on WILD Pokemon (the battle line says WILD);
  in a trainer battle they are simply lost. Only throw a ball when
  the current goal is a catching goal.
- Anything that CONFIRMS something (take, buy, learn, a yes/no about
  a specific choice) gets ONE press after READING what the screen
  names - never a mash.
- POISONED outside battle: use_antidote does the whole cure in one
  behavior (once the bag has one) - or any Pokemon Center. Do not
  walk it off; it drains HP.
- Buy ONLY what a goal lists. Nothing else.
- Nickname prompts: NO (press B). If a letter grid ever opens
  anyway: B only deletes letters - escape with press_A, press_START,
  press_A.
- Leaving a building puts you ON its doorstep: a step UP walks back
  in. Step away first.
- In the little gate buildings the door you WANT is the far one, and
  walk_to_exit always picks the NEAR one - never use it inside a
  gate; cross the room with plain walks and step through the doorway
  ahead.
- OUTDOORS in a town, never use walk_to_exit - outdoors it walks
  INTO the nearest building door. Between buildings use landmark
  walks or plain walks.
- Mark a goal done when, as far as you can tell, its DONE line
  happened - the coach checks every stamp and fixes mistakes, so an
  honest wrong stamp costs nothing. What you must NEVER do is stamp
  a goal to escape it because it feels hard - that is what the
  "COACH:" flag is for.

--- PASTE ENDS ---

## Waypoints appendix (copy into the run's waypoints.yaml)

```yaml
# Checkpoint-curated waypoints (HOT). Bearings render same-map only,
# and each same-map waypoint mints a walk_to_<name> landmark walk -
# keep this list SMALL and durable. Act 0 set; prune the lab/grass
# scaffolds at the Act 1 mint. Coords VERIFIED live in the limits
# runs (git: limits-4 waypoints.yaml @ a58a70d) unless marked GUESS.
waypoints:
  Oak's lab door: {map: 0, x: 12, y: 11}
  Oak: {map: 40, x: 5, y: 2}            # GUESS +-1; adjacent talk works
  the grass at the top of town: {map: 0, x: 10, y: 1}   # GUESS: Route 1 gap column
  gap to Pallet Town: {map: 12, x: 10, y: 35}
  gap to Viridian: {map: 12, x: 11, y: 2}
  Viridian Mart door: {map: 1, x: 29, y: 19}
  Viridian Center door: {map: 1, x: 23, y: 25}
  south gap to Route 1: {map: 1, x: 21, y: 35}
  gap to Route 22: {map: 1, x: 0, y: 17}   # GUESS: west road row; eyeball first crossing
```
