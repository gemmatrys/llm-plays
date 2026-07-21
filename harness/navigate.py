"""Harness-side pathfinding: the model picks a DESTINATION, not button presses.

Watching the 31B "calculate" routes in its thinking was the single biggest
latency sink after stale goals — spatial BFS is exactly what a deterministic
harness does in microseconds and a language model does in thousands of tokens.
The library exposes navigation behaviors (walk_north/south/east/west,
walk_to_exit) as stubs; when the model picks one, the loop swaps in a real
path computed here over the SAME block-walkability grid the ASCII map is
rendered from (terrain table + NPC blocks + off-map border, block bottom-left
convention). walk_<dir> goes to the farthest reachable on-screen block in that
direction, routing around trees/ledges/people; walk_to_exit goes to the
nearest reachable warp. Paths are capped so the model re-reads the world every
dozen tiles, and an unreachable direction degrades to explicit feedback
("[walk_north: no path visible]") instead of silent failure.
"""
from __future__ import annotations

import random
from collections import deque

from .tilemap import _map_coord
from .types import Behavior, Step

NAV_BEHAVIORS = ("walk_north", "walk_south", "walk_west", "walk_east",
                 "walk_to_exit", "walk_to_counter", "walk_to_grass")
MAX_STEPS = 12  # re-decide after ~a screen's worth of walking


def parse(name: str) -> tuple[str, int | None]:
    """Split an optional tile count off a nav name: "walk_east_3" ->
    ("walk_east", 3); plain names -> (name, None). Lets the model walk an
    exact bearing distance instead of always going as far as possible."""
    base, _, tail = name.rpartition("_")
    if base in ("walk_north", "walk_south", "walk_west", "walk_east") \
            and tail.isdigit() and 1 <= int(tail) <= 9:
        return base, int(tail)
    return name, None


def is_nav(name: str) -> bool:
    return parse(name)[0] in NAV_BEHAVIORS

_DIRS = (("UP", 0, -1), ("DOWN", 0, 1), ("LEFT", -1, 0), ("RIGHT", 1, 0))


def _block_grid(tiles: bytes, cfg, walkable: set[int],
                npcs: list[tuple[int, int]],
                map_wh: tuple[int, int] | None,
                player: tuple[int, int] | None,
                warp_blocks: set[tuple[int, int]]) -> list[list[bool]]:
    cols_b, rows_b = cfg.cols // 2, cfg.rows // 2
    npcset = {(c + dc, r + dr) for c, r in npcs
              for dc in (0, 1) for dr in (0, 1)}
    grid = [[False] * cols_b for _ in range(rows_b)]
    for br in range(rows_b):
        for bc in range(cols_b):
            if (bc * 2, br * 2) in npcset:
                continue  # a person stands there; they wander, we re-path
            if map_wh is not None and player is not None:
                mx, my = _map_coord(bc * 2, br * 2, cfg, *player)
                if mx < 0 or mx >= map_wh[0] or my < 0 or my >= map_wh[1]:
                    continue  # off-map border
            bl = tiles[(br * 2 + 1) * cfg.cols + bc * 2]
            # warp blocks count as open even when their tile id (stairs, door
            # mat) isn't in the walkable set — they are the point of walking
            if bl in walkable or (bc, br) in warp_blocks:
                grid[br][bc] = True
    return grid


def _bfs(grid: list[list[bool]], start: tuple[int, int],
         ledge_blocks: set[tuple[int, int]] = frozenset()):
    """BFS over walkable blocks. Ledges are one-way edges: pressing DOWN
    while standing above one hops the player over it (landing two blocks
    down) — recorded as direction "DOWN*" so the route can give the hop
    animation extra settle time. From below, a ledge is just a wall."""
    dist = {start: 0}
    parents: dict[tuple[int, int], tuple[tuple[int, int], str] | None] = \
        {start: None}
    q = deque([start])
    while q:
        c, r = q.popleft()
        for name, dx, dy in _DIRS:
            n = (c + dx, r + dy)
            if not (0 <= n[0] < len(grid[0]) and 0 <= n[1] < len(grid)):
                continue
            if grid[n[1]][n[0]] and n not in dist:
                dist[n] = dist[(c, r)] + 1
                parents[n] = ((c, r), name)
                q.append(n)
            elif name == "DOWN" and n in ledge_blocks:
                n2 = (c, r + 2)
                if (n2[1] < len(grid) and grid[n2[1]][n2[0]]
                        and n2 not in dist):
                    dist[n2] = dist[(c, r)] + 1
                    parents[n2] = ((c, r), "DOWN*")
                    q.append(n2)
    return dist, parents


def _route(parents, goal) -> list[str]:
    seq: list[str] = []
    node = goal
    while parents[node] is not None:
        node, direction = parents[node]
        seq.append(direction)
    return list(reversed(seq))


def _dist_to_set(grid: list[list[bool]],
                 goals: set[tuple[int, int]]) -> dict[tuple[int, int], int]:
    """Multi-source BFS: distance from every walkable block to the NEAREST
    goal block. Membership in the result == reachable."""
    dist: dict[tuple[int, int], int] = {}
    q: deque = deque()
    for g in goals:
        if 0 <= g[1] < len(grid) and 0 <= g[0] < len(grid[0]):
            dist[g] = 0
            q.append(g)
    while q:
        c, r = q.popleft()
        for _, dx, dy in _DIRS:
            n = (c + dx, r + dy)
            if (0 <= n[0] < len(grid[0]) and 0 <= n[1] < len(grid)
                    and grid[n[1]][n[0]] and n not in dist):
                dist[n] = dist[(c, r)] + 1
                q.append(n)
    return dist


def _stochastic_route(start: tuple[int, int],
                      field: dict[tuple[int, int], int],
                      max_steps: int) -> tuple[list[str], tuple[int, int]]:
    """Random descent over a BFS distance field: each step picks randomly
    among neighbors that are closer OR level (never the block just left).
    The grid can lie about single tiles — warp mats are force-opened but a
    gate doorway proved game-blocked from below (the (4,1) wedge) — and a
    deterministic shortest path replays the same bump forever; a re-rolled
    random descent slides around the liar within a retry or two.
    Returns (button sequence, expected end block)."""
    seq: list[str] = []
    cur, prev = start, None
    for _ in range(max_steps):
        d = field.get(cur)
        if d is None or d == 0:
            break
        opts = []
        for name, dx, dy in _DIRS:
            n = (cur[0] + dx, cur[1] + dy)
            nd = field.get(n)
            if nd is None or n == prev or nd > d:
                continue
            opts.append((n, name))
        if not opts:
            break
        nxt, button = random.choice(opts)
        seq.append(button)
        prev, cur = cur, nxt
    return seq, cur


def _edge_press(wx: int, wy: int, map_wh: tuple[int, int] | None) -> str | None:
    """The outward button for a warp sitting on a map edge, or None for an
    interior warp. Edge doormats (e.g. the Poke Center's) don't fire on
    step-on — the player must walk OFF the edge from the mat; instant warps
    (house mats, stairs) fire during the transition anyway, so an extra
    outward press after them is harmless (buttons are ignored mid-warp)."""
    if map_wh is None:
        return None
    mw, mh = map_wh
    if wy >= mh - 1:
        return "DOWN"
    if wy <= 0:
        return "UP"
    if wx <= 0:
        return "LEFT"
    if wx >= mw - 1:
        return "RIGHT"
    return None


def resolve(name: str, tiles: bytes, cfg, walkable: set[int],
            npcs: list[tuple[int, int]],
            map_wh: tuple[int, int] | None,
            player: tuple[int, int] | None,
            warps: list[tuple[int, int]],
            ledges: set[int] = frozenset(),
            counters: set[int] = frozenset(),
            grasses: set[int] = frozenset(),
            grass_hint: tuple[int, int] | None = None) -> Behavior | None:
    """Turn a navigation behavior name into a concrete button path, or None
    when no on-screen path exists (caller reports that to the model).
    `counters`/`grasses` are this tileset's counter and wild-grass tile
    ids (the game's own tileset-header lists) — consumed by
    walk_to_counter and walk_to_grass."""
    orig = name
    name, count = parse(name)
    if name not in NAV_BEHAVIORS or not walkable:
        return None
    if name == "walk_to_counter" and not counters:
        return None  # this tileset has no counters (game's own header list)
    if name == "walk_to_grass" and not grasses:
        return None  # this tileset has no wild grass
    start = (cfg.player_col // 2, cfg.player_row // 2)
    warp_blocks: set[tuple[int, int]] = set()
    warp_at: dict[tuple[int, int], tuple[int, int]] = {}
    if player is not None:
        px, py = player
        for wx, wy in warps:
            sc, sr = cfg.player_col + (wx - px) * 2, cfg.player_row + (wy - py) * 2
            if 0 <= sc < cfg.cols and 0 <= sr < cfg.rows:
                warp_blocks.add((sc // 2, sr // 2))
                warp_at[(sc // 2, sr // 2)] = (wx, wy)

    # already STANDING on a warp (walk_to_exit used to answer "no path" here,
    # wedging the model on doormats): the exit is one outward press away
    if (name == "walk_to_exit" and player is not None
            and (px, py) in set(warps)):
        press = _edge_press(px, py, map_wh)
        if press is not None:
            # hold long enough to turn AND walk (a short tap only turns)
            return Behavior(name=orig, source="builtin",
                            steps=[Step(button=press, hold_frames=16,
                                        wait_frames=8)])

    grid = _block_grid(tiles, cfg, walkable, npcs, map_wh, player, warp_blocks)
    grid[start[1]][start[0]] = True  # you can always stand where you stand
    ledge_blocks: set[tuple[int, int]] = set()
    if ledges:
        for br in range(cfg.rows // 2):
            for bc in range(cfg.cols // 2):
                if tiles[(br * 2 + 1) * cfg.cols + bc * 2] in ledges:
                    ledge_blocks.add((bc, br))
    dist, parents = _bfs(grid, start, ledge_blocks)

    goal: tuple[int, int] | None = None
    counter_face: str | None = None
    if name == "walk_to_counter":
        # [person][counter tile][open space] in a straight line — the Gen 1
        # talk-across-the-counter geometry, using the game's own counter
        # tile ids from the tileset headers. Walk to the space, face the
        # person, stop. Matches the nurse and the mart clerk and nothing
        # else in the room (shoppers have no counter beside them).
        _btn = {(0, -1): "UP", (0, 1): "DOWN", (-1, 0): "LEFT", (1, 0): "RIGHT"}
        cols_b, rows_b = cfg.cols // 2, cfg.rows // 2
        spaces: dict[tuple[int, int], str] = {}  # standing block -> face btn
        for nc, nr in {(c // 2, r // 2) for c, r in npcs}:
            for _, dx, dy in _DIRS:
                b1 = (nc + dx, nr + dy)          # would-be counter block
                b2 = (nc + 2 * dx, nr + 2 * dy)  # would-be standing space
                if not (0 <= b1[0] < cols_b and 0 <= b1[1] < rows_b
                        and 0 <= b2[0] < cols_b and 0 <= b2[1] < rows_b):
                    continue
                if tiles[(b1[1] * 2 + 1) * cfg.cols + b1[0] * 2] not in counters:
                    continue
                if b2 == start or b2 in dist:
                    spaces.setdefault(b2, _btn[(-dx, -dy)])
        if not spaces:
            # person not on screen yet (the window is 10x9 blocks — right
            # at the door the nurse can sit past it): walk a few blocks
            # NORTH, where every Gen 1 interior keeps its counter, and the
            # next walk_to_counter call re-searches with more room visible
            north = [b for b in dist
                     if b != start and 0 < (start[1] - b[1]) <= 3]
            if north:
                goal = min(north, key=lambda b: (-(start[1] - b[1]), dist[b]))
            else:
                # wall ahead or nothing reachable: one direct press still
                # turns/steps north; the model re-reads the world after
                return Behavior(name=orig, source="builtin",
                                steps=[Step(button="UP", hold_frames=16,
                                            wait_frames=8)])
        else:
            if start in spaces:
                # already on the spot: a short tap turns in place to face
                # the counter (a long hold would step)
                return Behavior(name=orig, source="builtin",
                                steps=[Step(button=spaces[start],
                                            hold_frames=4, wait_frames=8)])
            field = _dist_to_set(grid, set(spaces))
            seq, end = _stochastic_route(start, field, MAX_STEPS)
            if not seq:
                return None
            steps = [Step(button=b, hold_frames=8, wait_frames=8)
                     for b in seq]
            if end in spaces:
                steps.append(Step(button=spaces[end], hold_frames=4,
                                  wait_frames=8))
            return Behavior(name=orig, source="builtin", steps=steps)
    elif name == "walk_to_grass":
        # nearest reachable wild-grass block. Standing in grass already?
        # start is excluded, so it walks to the NEXT patch — calling it
        # repeatedly paces through the grass, which is what starts wild
        # battles.
        gset = {b for b in dist
                if b != start
                and tiles[(b[1] * 2 + 1) * cfg.cols + b[0] * 2] in grasses}
        if gset:
            field = _dist_to_set(grid, gset)
            seq, end = _stochastic_route(start, field, MAX_STEPS)
            # don't stop at the edge: keep pacing INSIDE the patch with a
            # random grass-only walk for the remaining budget — walking
            # through grass is what rolls wild encounters; arriving at the
            # border tile rolls one check at most
            cur, prev = end, None
            for _ in range(MAX_STEPS - len(seq)):
                opts = []
                for bname, dx, dy in _DIRS:
                    n = (cur[0] + dx, cur[1] + dy)
                    if n == prev or n not in field:
                        continue
                    if tiles[(n[1] * 2 + 1) * cfg.cols + n[0] * 2] in grasses:
                        opts.append((n, bname))
                if not opts:
                    break
                nxt, button = random.choice(opts)
                seq.append(button)
                prev, cur = cur, nxt
            if not seq:
                return None
            return Behavior(name=orig, source="builtin",
                            steps=[Step(button=b, hold_frames=8,
                                        wait_frames=8) for b in seq])
        elif grass_hint is not None and player is not None:
            # no grass on screen, but we HAVE seen some on this map: head
            # toward the remembered patch by map coords — the next call
            # sees it on screen and finishes the job
            hx, hy = grass_hint
            tb = ((cfg.player_col + (hx - px) * 2) // 2,
                  (cfg.player_row + (hy - py) * 2) // 2)
            toward = [b for b in dist if b != start]
            if not toward:
                return None
            goal = min(toward, key=lambda b: (abs(b[0] - tb[0])
                                              + abs(b[1] - tb[1]), dist[b]))
        else:
            # never seen grass on this map — the loop tells the model so
            return None
    elif name == "walk_to_exit":
        reach = {b for b in warp_blocks if b in dist and b != start}
        if reach:
            # target the SET of exits, not one chosen warp: a doorway pair
            # like the forest gate's (4,0)/(5,0) has one mat game-blocked
            # from below — the random descent over the set finds whichever
            # side actually lets you through
            field = _dist_to_set(grid, reach)
            seq, end = _stochastic_route(start, field, MAX_STEPS)
            if seq:
                steps = [Step(button=b, hold_frames=8, wait_frames=8)
                         for b in seq]
                if end in warp_at:
                    press = _edge_press(*warp_at[end], map_wh)
                    if press is not None:
                        steps.append(Step(button=press, hold_frames=16,
                                          wait_frames=8))
                return Behavior(name=orig, source="builtin", steps=steps)
        if warps and player is not None:
            # no warp on screen (a small room's far corner puts its own
            # doormat one row past the 20x18 window): head TOWARD the
            # nearest warp by map coords — the next call sees it on screen
            # and the edge-press logic finishes the exit
            wx, wy = min(warps, key=lambda w: abs(w[0] - px) + abs(w[1] - py))
            tb = ((cfg.player_col + (wx - px) * 2) // 2,
                  (cfg.player_row + (wy - py) * 2) // 2)
            toward = [b for b in dist if b != start]
            if toward:
                goal = min(toward, key=lambda b: (abs(b[0] - tb[0])
                                                  + abs(b[1] - tb[1]), dist[b]))
    else:
        axis, sign = {"walk_north": (1, -1), "walk_south": (1, 1),
                      "walk_west": (0, -1), "walk_east": (0, 1)}[name]
        cands = [b for b in dist
                 if b != start and 0 < sign * (b[axis] - start[axis])
                 and (count is None
                      or sign * (b[axis] - start[axis]) <= count)]
        if cands:
            # farthest progress along the axis (capped at `count` tiles when
            # the model asked for an exact distance), shortest path tiebreak
            goal = min(cands, key=lambda b: (-sign * (b[axis] - start[axis]),
                                             dist[b]))
    if goal is None:
        if name not in ("walk_to_exit", "walk_to_counter"):
            # BFS sees nothing reachable that way, but the world continues
            # past the map edge (town/route connections live there — they
            # are not warps and render as nothing). Fall back to ONE direct
            # step: at an edge it crosses the connection; against a real
            # wall it bumps once and "[move blocked]" says so. Hold long
            # enough to turn AND walk.
            btn = {"walk_north": "UP", "walk_south": "DOWN",
                   "walk_west": "LEFT", "walk_east": "RIGHT"}[name]
            return Behavior(name=orig, source="builtin",
                            steps=[Step(button=btn, hold_frames=16,
                                        wait_frames=8)])
        return None
    full = _route(parents, goal)
    seq = full[:MAX_STEPS]
    if not seq:
        return None
    # "DOWN*" = ledge hop: one press, but the jump animation needs settle
    # time before the next input or the rest of the path desyncs
    steps = [Step(button=d.rstrip("*"), hold_frames=8,
                  wait_frames=30 if d.endswith("*") else 8) for d in seq]
    # finish the job: after stepping onto an edge warp, walk off the edge —
    # only when the route actually reaches the warp (not truncated)
    if (name == "walk_to_exit" and len(full) <= MAX_STEPS
            and goal in warp_at):
        press = _edge_press(*warp_at[goal], map_wh)
        if press is not None:
            steps.append(Step(button=press, hold_frames=16, wait_frames=8))
    # finish the job: on arriving at the counter spot, a short tap turns to
    # face across the counter — only when the route actually got there
    if (name == "walk_to_counter" and len(full) <= MAX_STEPS
            and counter_face is not None):
        steps.append(Step(button=counter_face, hold_frames=4, wait_frames=8))
    return Behavior(name=orig, source="builtin", steps=steps)
