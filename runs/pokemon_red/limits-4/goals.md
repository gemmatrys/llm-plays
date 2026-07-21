# Goals

11. [DONE] Grind to level 14+ in Viridian Forest.
12. [DONE] Reach the forest's west side.
13. [DONE] Exit the forest.
14. [DONE] Cross the gate to Route 2.
15. [DONE] Walk Route 2 north into Pewter City.
16. [DONE] Heal at the Pewter Center - EMBER's PP is refilled.

17. [DONE] Buy POTIONs at the Pewter Mart - the bag holds 6.

18. [DONE] Stand beside the Pewter Mart's door (the gym is entered from this
    street): use walk_to_pewter_mart_door, repeating until the "Pewter
    Mart door" bearing reads 2 tiles or less. Do NOT go inside. DONE
    when that bearing reads 2 or less: mark it done then.

19. Walk to the gym's doormat: use
    walk_to_the_doormat_below_the_gym_entrance, repeating until "the
    doormat below the Gym entrance" reads "you are here". It walks the
    open row west from the Mart's street. A CITIZEN strolls this
    street: when a walk stops early because someone stands in the way,
    do NOT reroute - people wander off; simply call
    walk_to_the_doormat_below_the_gym_entrance again, as many times as
    it takes. Never walk NORTH around the gym (dead end), and do not
    use walk_to_pewter_mart_door again - goal 18 is finished. The
    bushes SOUTH cannot be crossed. DONE when the doormat bearing
    reads "you are here": mark it done then.

20. Enter the gym: use enter_door_above - one behavior, it steps
    through the door above you and checks you are inside. DONE when
    your location reads Pewter Gym: mark it done then.

21. Reach BROCK inside the gym: walk toward the "Brock" bearing; the
    JR TRAINER who stops you must be beaten (trainer battles cannot be
    fled - the battle drill in Rules answers every turn). If you are
    below half HP after his fight, step out, heal at the Center, come
    back (beaten trainers stay beaten). DONE when the "Brock" bearing
    reads 2 tiles or less: mark it done then.

22. Beat BROCK for the BOULDERBADGE: talk to him. His GEODUDE (L12)
    and ONIX (L14) resist EMBER - the "About this battle" note will
    say so - use EMBER (attack_3) anyway: their special defense is
    terrible, it still wins, and everything else you have is worse.
    When ONIX is "storing energy" that is BIDE - it returns DOUBLE the
    damage it just took; that turn is the perfect time for use_potion
    instead of attacking. Use use_potion whenever you fall below half
    HP. If you black out you wake at the Center with half your money
    gone - heal and march back; after TWO losses, grind the forest to
    level 16 first (CHARMANDER evolves) and try again. DONE when the
    badge announcement and the TM he hands over ("[bag: +1 ...]")
    happened on screen: mark it done then.

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
- OUTDOORS in a town, never use walk_to_exit - outdoors it walks INTO
  the nearest building door (this is how you re-entered the Center
  four times and the Mart once). Between buildings use plain walks on
  the door bearing, its bigger number first; a building's own door
  swallows walks in the column above it, so clear the column sideways
  first.
- Do NOT mark a goal done unless its DONE line happened on screen. "I
  think I did it" is not evidence.
