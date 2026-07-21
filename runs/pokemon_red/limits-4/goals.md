# Goals

11. [DONE] Grind to level 14+ in Viridian Forest.
12. [DONE] Reach the forest's west side.
13. [DONE] Exit the forest.
14. [DONE] Cross the gate to Route 2.
15. [DONE] Walk Route 2 north into Pewter City.
16. [DONE] Heal at the Pewter Center - EMBER's PP is refilled.

17. Buy 5 POTIONs at the Pewter MART (the "Pewter Mart door" bearing).
    Getting there, from outside the Center: NEVER use walk_to_exit
    while you are outdoors - outdoors it walks INTO the nearest
    building door, which is how you have re-entered the Center four
    times. Use plain walks only. First walk EAST to the "east of the
    Center" landmark; only then follow the "Pewter Mart door" bearing
    (its east part before its north part - the Center door sits in the
    column just north of you and swallows northbound walks). Inside, use walk_to_counter, then
    buy_potion_x5 - it holds the
    whole conversation and purchase, one behavior, 1500 total. If the
    bag event shows FEWER than you asked (a "[bag: +1 POTION]" for a
    x5 ask), just call it again - repeat until the bag line reads
    POTION x5, then mark done. Your money covers it.
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
    time for use_potion instead of attacking - it drinks a POTION and
    plays the turn out, one behavior. Use it whenever you fall below
    half HP. If you black
    out you wake at the Center with half your money gone - heal and
    march back; after TWO losses, grind the forest to level 16 first
    (CHARMANDER evolves) and try again. The badge announcement and the
    TM he hands over ("[bag: +1 ...]") are the proof - mark done then.

Rules:
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
- In the little gate buildings the door you WANT is the far one, and
  walk_to_exit always picks the NEAR one - never use it inside a gate;
  cross the room with plain walks and step through the doorway ahead.
- Do NOT mark a goal done unless its DONE line happened on screen. "I
  think I did it" is not evidence.
