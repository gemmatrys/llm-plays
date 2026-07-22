# Quest tree — Pokémon Red, Bulbasaur run (next run)

Checkpoint-owned master plan AND progression ledger. The run's goals.md
atoms are minted from this tree one at a time; when a node's goals are
validated done, the checkpoint marks it here with the goal numbers that
delivered it — so this file reads as the progression of everything we
asked the local LLM to do and it did successfully.

Legend: [x] done (validated, goals noted) | [>] in progress | [ ] planned.
EVERY node carries `verify:` — the evidence that settles it. Act-level
verifies are the checkpoint's stamp-validation anchors (RAM badges byte,
bag events, party reads); leaf verifies become the minted goals' DONE
lines. A quest without a verify is not a quest.
Coordinates and screen facts marked GUESS need live verification; the
starter drill especially: READ THE LABEL, never mash a confirm.

MODEL-FACING DERIVATION (this file is checkpoint-voice; the model gets
a derived view in the goals.md preamble - the run-1 learnings, applied):
- ACT GRANULARITY ONLY. The model's tree shows acts, never leaves -
  sub-goals churn constantly (ten rewrites in one gym afternoon); the
  act list never does. Goal restructuring must never touch the tree
  text the model reads.
- Use each act's `player:` line VERBATIM - pre-written player voice,
  stable across checkpoints and cache-friendly. Never re-word live.
- Done acts collapse to one "Done:" line (the prune lesson: stamped
  text left in the prompt correlated with thinking-budget failures);
  the CURRENT act is marked YOU ARE HERE; future acts stay one line
  each; checkpoint annotations (risks, GUESS, wedge classes, ledgers,
  verify lines) are NEVER sent - leaf verifies surface as the minted
  goals' DONE lines when their act arrives.
- Everything sent obeys the state-line vocabulary: place names exactly
  as the location line says them, no coordinates, no jargon.

- [ ] BEAT THE GAME — defeat the Elite Four at Indigo Plateau
      verify: Hall of Fame entered (credits rolled; post-champion save;
      RAM hall-of-fame flag once its address is verified)
  - [ ] ACT 0 — Bulbasaur and the errand loop (Pallet/Viridian)
        player: start the journey - choose BULBASAUR and finish
        Oak's errand
        verify: team line shows BULBASAUR; Pokedex obtained; owned
        species >= 3; POKE BALLs in bag
    - [ ] New game: preset name, mash-safe dialogue until the lab
          verify: location reads Oak's lab, no dialogue open
    - [ ] STARTER = BULBASAUR, verified: at each ball press A to READ
          its label; confirm YES only when the screen names BULBASAUR
          (limits-4 mash-A accidentally took Charmander - the drill is
          label-first, position assumptions banned)
          verify: team line shows BULBASAUR (and nothing else)
    - [ ] Rival battle 1 (he takes Charmander vs our Bulbasaur): Tackle
          it out; a loss costs money only - acceptable
          verify: battle over, location still the lab (win or loss)
    - [ ] Oak's parcel: Viridian mart, deliver back, receive Pokedex
          verify: bag events +PARCEL then -PARCEL; Pokedex in the
          START menu afterward
    - [ ] Buy Poke Balls; catch 2-3 on Routes 1/22 (Pidgey/Rattata/
          Nidoran - species count feeds the Flash aide later)
          verify: bag shows POKE BALLs; party count >= 2; owned >= 3
  - [ ] ACT 1 — BOULDER badge (Brock, Pewter)
        player: win the BOULDER badge from Brock in Pewter City
        verify: RAM badges 0 -> 1 (BOULDER bit); TM34 bag event
    - [ ] Route 2 south + Viridian Forest (catch Pikachu if seen -
          lategame flyer/water answer; grind Bulbasaur to L13: VINE
          WHIP arrives at 13 and trivializes this act)
          verify: location reads Pewter City; team line shows L13+ and
          VINE WHIP on the move list
    - [ ] Pewter: heal, restock
          verify: team at full HP; potions in bag
    - [ ] Brock: Vine Whip 2-hit-KOs Geodude and Onix. Target L13-14.
          (If entry wedges: the east-road badge-gate man DRAGS you to
          the gym - walk east toward Route 3 and let him)
          verify: badge announcement + "[bag: +1 TM34]"; badges byte
          confirms
  - [ ] ACT 2 — CASCADE badge (Misty, Cerulean)
        player: cross Mt. Moon and win the CASCADE badge from Misty
        in Cerulean City
        verify: badges byte has CASCADE; TM11 bag event
    - [ ] Route 3 trainer gauntlet (6 trainers; heal after)
          verify: location reads Route 4 side (Pokemon Center by Mt.
          Moon); team healed
    - [ ] Mt. Moon: 3 floors, Team Rocket, fossil choice (either is
          fine; do not lose the Moon Stone hunt time) - exit Route 4
          verify: location reads Route 4 east side; a fossil in bag
    - [ ] Cerulean: heal; evolve check (Ivysaur at L16)
          verify: location reads Cerulean City; team line shows
          IVYSAUR when L16+
    - [ ] Misty: Staryu L18 / Starmie L21 - Vine Whip advantage again.
          Target L18-20. BubbleBeam TM is a keeper for a future water
          catch
          verify: badge announcement + TM11 bag event; badges byte
  - [ ] ACT 3 — THUNDER badge (Lt. Surge, Vermilion)
        player: meet Bill, sail the S.S. Anne, and win the THUNDER
        badge from Lt. Surge in Vermilion City
        verify: badges byte has THUNDER; HM01 and TM24 bag events;
        S.S. TICKET consumed
    - [ ] Nugget Bridge + Routes 24/25 -> Bill's cottage (S.S. Ticket)
          verify: S.S. TICKET bag event; NUGGET bag event en route
    - [ ] Cerulean rocket (backyard dig house), Routes 5/6 south
          verify: location reads Vermilion City
    - [ ] Vermilion; S.S. Anne: rival battle 2, the Captain -> HM01 CUT
          (the ship LEAVES after - get the HM before exiting)
          verify: HM01 bag event BEFORE leaving the ship
    - [ ] Teach CUT to Bulbasaur/Ivysaur (it learns it; no filler catch
          needed); cut into the gym
          verify: CUT on the team line's move list; location reads
          Vermilion Gym
    - [ ] Surge gym trash-can switch hunt: KNOWN WEDGE CLASS (hidden
          2nd switch adjacent to the 1st, resets on miss) - goals must
          carry the adjacent-can drill; electric vs part-poison Ivysaur
          is survivable. Target L22-24
          verify: badge announcement + TM24 bag event; badges byte
  - [ ] ACT 4 — RAINBOW badge (Erika, Celadon)
        player: reach Celadon City through Rock Tunnel and win the
        RAINBOW badge from Erika
        verify: badges byte has RAINBOW; TM21 bag event; HM05 in bag
    - [ ] Route 2 aide: HM05 FLASH at 10 owned species - plan catches
          to reach 10 BEFORE Rock Tunnel (species-count subgoal)
          verify: owned species >= 10 (RAM Pokedex count); HM05 bag
          event; FLASH taught to someone
    - [ ] Routes 9/10; Rock Tunnel WITH Flash (dark maze without it is
          a model-killer - do not attempt unlit)
          verify: location reads Lavender Town
    - [ ] Lavender (tower is ghost-blocked - note and move on),
          Route 8 west to Celadon
          verify: location reads Celadon City
    - [ ] Celadon errands: dept. store TMs, roof drinks (one saved for
          the Saffron guard)
          verify: a drink in bag (FRESH WATER/SODA/LEMONADE events)
    - [ ] Erika: grass-vs-grass slog RISK - Ivysaur resists but cannot
          hit hard; bring the Pikachu or a Pidgeotto with Gust/Wing
          Attack as second attacker. Target L26-29
          verify: badge announcement + TM21 bag event; badges byte
  - [ ] ACT 5 — story gates (Rocket, ghosts, the Flute)
        player: drive Team Rocket from Celadon, lay the Pokemon
        Tower ghost to rest, and wake the sleeping Snorlax
        verify: SILPH SCOPE and POKE FLUTE bag events; a Snorlax
        route open (crossed it)
    - [ ] Game Corner hideout: lift key, Giovanni fight 1 -> SILPH SCOPE
          verify: LIFT KEY then SILPH SCOPE bag events
    - [ ] Pokemon Tower: rival battle 3, Marowak ghost (Scope), Mr.
          Fuji -> POKE FLUTE
          verify: POKE FLUTE bag event; location read Pokemon Tower
          top floor during
    - [ ] Snorlax (Route 12 OR 16): flute, then fight-or-flee; catching
          it is a luxury, not a requirement
          verify: crossed the tile it blocked (location past it);
          optionally SNORLAX on team
  - [ ] ACT 6 — SOUL badge (Koga, Fuchsia)
        player: reach Fuchsia City, learn to SURF at the Safari
        Zone, and win the SOUL badge from Koga
        verify: badges byte has SOUL; HM03 + HM04 + TM06 bag events
    - [ ] South to Fuchsia: Routes 12/13/14/15 (no bike dependency)
          verify: location reads Fuchsia City
    - [ ] Safari Zone run: HM03 SURF (secret house) + GOLD TEETH ->
          warden -> HM04 STRENGTH. Step-limited zone: goals must route
          directly, no wandering
          verify: HM03 and GOLD TEETH bag events in-zone; HM04 bag
          event at the warden
    - [ ] Koga: invisible-wall maze (walk the walls patiently);
          poison-vs-poison is safe but slow. Target L35-38
          verify: badge announcement + TM06 bag event; badges byte
  - [ ] ACT 7 — MARSH badge (Sabrina, Saffron)
        player: free Silph Co. from Team Rocket and win the MARSH
        badge from Sabrina in Saffron City
        verify: badges byte has MARSH; MASTER BALL + TM46 bag events;
        LAPRAS on team or in box
    - [ ] Saffron guard: hand over a Celadon roof drink
          verify: drink bag event (-1); location reads Saffron City
    - [ ] Silph Co: 11 floors, card key shortcuts, rival battle 4,
          Giovanni fight 2 -> MASTER BALL (save it; Lapras gift on 7F
          is a strong Surf-carrier - TAKE IT)
          verify: CARD KEY, LAPRAS (party/box read), MASTER BALL
          events; Silph exit dialogue done
    - [ ] Sabrina: PSYCHIC vs our poison typing is the run's worst
          matchup - lead with Lapras/Snorlax/Pidgeot, keep Venusaur
          back. Teleport-pad maze: goals carry the pad route. Target
          L38-42
          verify: badge announcement + TM46 bag event; badges byte
  - [ ] ACT 8 — VOLCANO badge (Blaine, Cinnabar)
        player: surf to Cinnabar Island, unlock the Mansion, and
        win the VOLCANO badge from Blaine
        verify: badges byte has VOLCANO; TM38 bag event
    - [ ] Teach SURF (Lapras ideal); Routes 19/20/21 south by water
          verify: SURF on a team move list; location reads Cinnabar
          Island
    - [ ] Pokemon Mansion: SECRET KEY maze (statue switches)
          verify: SECRET KEY bag event
    - [ ] Blaine: fire vs grass is BAD - this is Lapras/water's gym.
          Target L40-44
          verify: badge announcement + TM38 bag event; badges byte
  - [ ] ACT 9 — EARTH badge (Giovanni, Viridian)
        player: win the EARTH badge from Giovanni in Viridian City
        verify: badges byte has all 8; TM27 bag event
    - [ ] Viridian gym now open: ground/rock vs Razor Leaf - Venusaur's
          gym. Giovanni fight 3. Target L43-46
          verify: badge announcement + TM27 bag event; badges byte = 8
  - [ ] ACT 10 — the end
        player: cross Victory Road and defeat the Elite Four
        verify: Hall of Fame (credits; post-champion save state)
    - [ ] Route 22 rival final; Route 23 badge-gate gauntlet
          verify: location reads Victory Road entrance
    - [ ] Victory Road: STRENGTH boulder puzzles (worst navigation in
          the game - goals must carry probed routes, one puzzle per
          goal)
          verify: location reads Indigo Plateau
    - [ ] Elite Four, in order: Lorelei (ICE - grass's nightmare: lead
          electric/Lapras), Bruno (rock/fighting - Venusaur eats it),
          Agatha (ghost/poison - patience), Lance (dragon/flying - Ice
          Beam TM on Lapras beforehand), Champion rival. Target L47-53
          verify: each Elite member's defeat dialogue; the champion's
          ending scene; Hall of Fame
- Cross-cutting, tracked here so no act forgets them:
  - [ ] TEAM PLAN around Venusaur: Pikachu (forest, early), a bird
        (Pidgey line, early), LAPRAS (Silph gift - Surf/Ice core),
        Snorlax optional tank. Ice Beam and Thunderbolt TMs are the
        two that matter
        verify: party reads at each act close match the plan (or the
        deviation is noted here with why)
  - [ ] HM ledger: CUT (SS Anne) -> FLASH (Route 2 aide, 10 species)
        -> SURF + STRENGTH (Safari) ; FLY optional if a bird sticks
        verify: each HM's bag event + the move on a team move list
  - [ ] KEY ITEMS ledger: S.S. Ticket, Silph Scope, Poke Flute, Gold
        Teeth, Secret Key, Card Key, Master Ball
        verify: each item's bag event at its act
  - [ ] Species-count subgoal: 10 owned before Rock Tunnel (Flash)
        verify: RAM Pokedex owned count >= 10
