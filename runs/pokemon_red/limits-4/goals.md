# Goals

11. [DONE] Grind until CHARMANDER is LEVEL 14 or higher - your team line is the proof.

12. [DONE] Get to the WEST SIDE of the forest. Follow "the west side path"
    bearing: walk the direction with the bigger number of tiles left;
    when a walk stops, read its report - the FIRST opening WEST is the
    way (walk the counted steps back to it, then turn west). The
    top-left pocket is CLOSED (trees block north and west up there) -
    never go back up. DONE when your west-east position reads x = 4 or
    less: mark it done then.

13. Walk NORTH up the west edge of the forest to the exit mats in the
    top-left corner (the "forest exit corner" bearing). Stepping onto
    the mats leaves the forest by itself. DONE the moment your
    location no longer reads Viridian Forest: mark it done then.

14. Cross the little gate building northward: cross the room, then use
    the far doorway ahead of you. DONE when your location reads
    Route 2: mark it done then.

15. Walk Route 2 NORTH into PEWTER CITY (the "gap to Pewter" bearing).
    Do NOT enter the cave door east of the path - its Pokemon are ten
    levels above you. Skip dark grass where the path allows and do not
    hunt battles. DONE when your location reads Pewter City: mark it
    done then.

16. Heal at the Pewter Pokemon Center (the "Pewter Center door"
    bearing): inside, walk_to_counter puts you in front of the nurse -
    talk, ONE press A on her yes/no, mash through the rest. She also
    refills EMBER's PP. DONE when the heal finished and your team line
    shows full HP: mark it done then.

17. Buy 5 POTIONs at the Pewter MART (the "Pewter Mart door" bearing):
    inside, use walk_to_counter, then buy_potion_x5 - it holds the
    whole conversation and purchase, one behavior, 1500 total. A
    "[bag: +5 POTION]" event is the proof - mark done when you see it.
    If you cannot afford it, move on without buying. Skip the MUSEUM -
    it only costs money.

18. Win the BOULDERBADGE at the Pewter GYM (the "Pewter Gym door"
    bearing). Inside, a JR TRAINER blocks the way - beat him, then if
    you are below half HP step out, heal at the Center and come back
    (beaten trainers stay beaten). Walk to BROCK (the "Brock" bearing)
    and talk to him. His GEODUDE (L12) and ONIX (L14) resist EMBER -
    the "About this battle" note will say so - use EMBER anyway: their
    special defense is terrible, it still wins, and everything else
    you have is worse. When ONIX is "storing energy" that is BIDE - it
    returns DOUBLE the damage it just took; that turn is the perfect
    time for use_potion_battle instead of attacking - it drinks a
    POTION and plays the turn out, one behavior. Use it whenever you
    fall below half HP. If you black
    out you wake at the Center with half your money gone - heal and
    march back; after TWO losses, grind the forest to level 16 first
    (CHARMANDER evolves) and try again. The badge announcement and the
    TM he hands over ("[bag: +1 ...]") are the proof - mark done then.

Rules:
- Until the goal-16 heal there are NO POTIONs in the bag and EMBER has
  0 PP - Potion rules do not apply, and a wild bug that jumps you:
  flee_battle escapes in one call, or attack_1 (SCRATCH) kills it in a
  turn or two - pick one and go, do not deliberate. These bugs cannot
  beat your CHARMANDER; keep walking.
- A fight the current goal does not say how to handle: attack_3
  (EMBER); at 0 PP, attack_1 (SCRATCH). When the goal names a battle
  drill, that drill IS the answer - use it without comparing.
- Poke Balls only work on WILD Pokemon (the battle line says WILD); in a
  trainer battle they are simply lost. Keep the last ball for a PIKACHU.
- POISONED outside battle: use_antidote does the whole cure in one
  behavior - use it right away, or any Pokemon Center. Do not walk it
  off; it drains HP.
- Potion early, not at the last moment - blacking out costs HALF your
  money.
- Buy ONLY what a goal lists. Nothing else, no museum tickets.
  Nickname prompts: NO.
- In the little gate buildings the door you WANT is the far one:
  cross the room first, then use the doorway ahead of you.
- Do NOT mark a goal done unless its DONE line happened on screen. "I
  think I did it" is not evidence.
