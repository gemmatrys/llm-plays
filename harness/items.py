"""Generalized item intents: `use_<item>` and `buy_<item>_x<n>`.

The model's vocabulary carries the ARGUMENTS in the name (the counted-walk
pattern: walk_east_3): `use_antidote`, `buy_potion_x5`. Names are minted
per decision from what is actually possible — the bag's contents make
`use_*` names, the shop table of the CURRENT map makes `buy_*` names — so
the grammar enum stays closed and the model can never name an item it
does not have or a shop does not sell. The harness owns the menu
geometry (runtime cursor math from the item's slot); the model owns the
choice of item, count, and moment. Replaces the first-generation static
skills (buy_potion_x5.yaml etc.) whose names this module resolves
identically — checkpoint-authored specifics were the scaffolding, this
is the general form (user directive 2026-07-21: "generalize it").

Menu geometry (Gen 1, no-wrap lists, cursors pinned with excess UPs):
  overworld use: START > pin > 2 DOWN (ITEM) > A > pin > slot DOWNs > A
                 > A (USE) > A (lead mon) > text > B B B out
  battle use:    collapse B B > pin FIGHT (UP LEFT) > DOWN (ITEM) > A
                 > pin > slot DOWNs > A > A (lead mon) > turn plays out
  buy:           (talking to the clerk already) A (BUY) > text > pin >
                 slot DOWNs > A > count-1 UPs > A > A (yes) > text > B B
"""
from __future__ import annotations

import re

from .types import Behavior, Step

_USE = re.compile(r"use_([a-z0-9_]+)$")
_BUY = re.compile(r"buy_([a-z0-9_]+)_x([1-9])$")

# skills that must keep their yaml/builtin meaning even though they match _USE
_RESERVED = {"use_pokecenter"}


def slug(item_name: str) -> str:
    """'POKE BALL' -> 'poke_ball' — the name fragment the model utters."""
    return re.sub(r"[^a-z0-9]+", "_", item_name.lower()).strip("_")


def is_item(name: str) -> bool:
    return name not in _RESERVED and bool(_USE.match(name) or _BUY.match(name))


def stub(name: str) -> Behavior | None:
    """Placeholder accepted at parse time; the loop swaps it for the real
    steps at execution, when bag/shop/battle context is known."""
    if not is_item(name):
        return None
    return Behavior(name=name, source="builtin", steps=[])


def dynamic_names(bag_names: list[str], mart_names: list[str]) -> list[str]:
    """The names that exist THIS decision. Counts 1-9 for buys."""
    out = [f"use_{slug(n)}" for n in bag_names]
    out += [f"buy_{slug(n)}_x{c}" for n in mart_names for c in range(1, 10)]
    return [n for n in out if n not in _RESERVED]


def legend(bag_names: list[str], mart_names: list[str]) -> list[str]:
    """Collapsed display lines for the prompt's behavior list."""
    out = []
    if bag_names:
        out.append("use_<item> (use an item from your bag on your lead "
                   "Pokemon - works in and out of battle; your bag: "
                   + ", ".join(slug(n) for n in bag_names) + ")")
    if mart_names:
        out.append("buy_<item>_x<1-9> (buy from the clerk you are talking "
                   "to - this shop sells: "
                   + ", ".join(slug(n) for n in mart_names) + ")")
    return out


def _press(btn: str, wait: int = 8) -> Step:
    return Step(button=btn, hold_frames=4, wait_frames=wait)


def _pin(count: int) -> list[Step]:
    return [_press("UP") for _ in range(count)]


def resolve(name: str, bag_names: list[str], mart_names: list[str],
            in_battle: bool) -> Behavior | None:
    """Real steps for an item intent, or None (with the reason in the
    feedback path) when the item is not actually there."""
    m = _USE.match(name)
    if m and name not in _RESERVED:
        want = m.group(1)
        slugs = [slug(n) for n in bag_names]
        if want not in slugs:
            return None  # not in the bag - fail loud at the caller
        slot = slugs.index(want)  # 0-based
        if in_battle:
            steps = [Step(op="advance_text"),
                     _press("B", 24), _press("B", 24),
                     _press("UP", 12), _press("LEFT", 12),  # pin FIGHT
                     _press("DOWN", 12),                    # ITEM
                     _press("A", 30),
                     Step(op="verify", wait_frames=15, abort_on_fail=True,
                          expect="the battle bag's item list is open")]
            steps += _pin(len(slugs))
            steps += [_press("DOWN") for _ in range(slot)]
            steps += [_press("A", 30), _press("A", 40)]     # item, lead mon
            steps += [Step(op="advance_text")]              # turn plays out
        else:
            steps = [_press("START", 30)]
            steps += _pin(6)                                # top of START menu
            steps += [_press("DOWN"), _press("DOWN"),       # ITEM
                      _press("A", 30),
                      Step(op="verify", wait_frames=15, abort_on_fail=True,
                           expect="the bag's item list is open")]
            steps += _pin(len(slugs))
            steps += [_press("DOWN") for _ in range(slot)]
            steps += [_press("A", 20), _press("A", 30),     # USE
                      _press("A", 40)]                      # lead mon
            steps += [Step(op="advance_text"),
                      _press("B", 20), _press("B", 20), _press("B", 20),
                      Step(op="verify", wait_frames=30,
                           expect="the overworld is on screen with no menu "
                                  "open")]
        return Behavior(name=name, source="builtin", steps=steps)
    m = _BUY.match(name)
    if m:
        want, count = m.group(1), int(m.group(2))
        slugs = [slug(n) for n in mart_names]
        if want not in slugs:
            return None  # this shop does not sell it
        slot = slugs.index(want)
        # two Bs first: collapse any half-open shop state (item list or
        # quantity box from an earlier buy) back to closed - the first
        # live retries no-op'd because A(BUY) landed into an already-open
        # list where focus sat on BUY/SELL/QUIT (the shop focus trap).
        # Judge checkpoints at every screen transition (user 2026-07-21):
        # the skill never fires steps into a screen it has not confirmed.
        steps = [_press("B", 20), _press("B", 20),
                 Step(op="advance_text"),                   # (re)greet -> menu
                 Step(op="verify", wait_frames=20, abort_on_fail=True,
                      expect="the shop's BUY/SELL/QUIT choice is on screen"),
                 _press("A", 30),                           # BUY (tops there)
                 Step(op="advance_text"),                   # -> item list
                 Step(op="verify", wait_frames=20, abort_on_fail=True,
                      expect="the shop's item list with prices is open")]
        steps += _pin(len(slugs))
        steps += [_press("DOWN") for _ in range(slot)]
        steps += [_press("A", 45)]                          # wait for the
        # quantity box to render before counting - a fast A ate the UPs on
        # the first live buy (x5 asked, x1 bought, 2026-07-21 Pewter)
        if count > 1:
            steps += [Step(op="verify", wait_frames=15, abort_on_fail=True,
                           expect="a how-many quantity box is on screen")]
        steps += [_press("UP", 14) for _ in range(count - 1)]
        steps += [_press("A", 30),                          # -> price yes/no
                  _press("A", 40),                          # yes
                  Step(op="advance_text"),                  # "here you are"
                  _press("B", 20), _press("B", 20),         # out of shop menus
                  Step(op="advance_text")]                  # "come again!"
        return Behavior(name=name, source="builtin", steps=steps)
    return None
