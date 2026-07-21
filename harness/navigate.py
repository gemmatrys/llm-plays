"""Harness-side pathfinding: the model picks a DESTINATION, not button presses.

Watching the 31B "calculate" routes in its thinking was the single biggest
latency sink after stale goals — spatial BFS is exactly what a deterministic
harness does in microseconds and a language model does in thousands of tokens.
The library exposes navigation behaviors (walk_north/south/east/west,
walk_to_exit) as stubs; when the model picks one, the loop swaps in a real
path computed here over the SAME block-walkability grid the ASCII map is
rendered from (terrain table + NPC blocks + off-map border, block bottom-left
convention). A plain walk_<dir> is a STRAIGHT STRIDE: exactly that direction
until a wall stops it (sidestepping lone single-block obstacles, hopping
ledges downward) — predictable motion whose stopping point is information;
counted variants (walk_east_3) stay BFS-exact for bearings; walk_to_* macros
BFS to their targets. Paths are capped so the model re-reads the world every
dozen tiles, and an unreachable direction degrades to explicit feedback
("[walk_north: no path visible]") instead of silent failure.
"""
from __future__ import annotations

import random
from collections import deque

from .tilemap import _map_coord
from .types import Behavior, Step

NAV_BEHAVIORS = ("walk_north", "walk_south", "walk_west", "walk_east",
                 "walk_to_exit", "walk_to_counter", "walk_to_grass",
                 "walk_to_mark")  # mark: BFS toward a named waypoint (map
                                  # coords via the `mark` kwarg); the model
                                  # utters walk_to_<landmark-slug>
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
            grass_hint: tuple[int, int] | None = None,
            mark: tuple[int, int] | None = None) -> Behavior | None:
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
    elif name == "walk_to_mark":
        # BFS toward a named waypoint (the model utters walk_to_<landmark>;
        # the loop passes the map coords). Stands ON the tile when it can;
        # a mark that cannot be stood on (a door mat, a sign-side tile) or
        # sits off screen gets "as close as the world allows" - the next
        # call converges further. Born from the Pewter gym door: 90 minutes
        # of prose could not walk a model beside a door it could see.
        if mark is None or player is None:
            return None
        tsc = cfg.player_col + (mark[0] - px) * 2
        tsr = cfg.player_row + (mark[1] - py) * 2
        tb = (tsc // 2, tsr // 2)
        if tb == start:
            return Behavior(name=orig, source="builtin",
                            steps=[Step(op="wait", wait_frames=8)],
                            note=f"[{orig}: you are standing at it]")
        if (0 <= tb[0] < cfg.cols // 2 and 0 <= tb[1] < cfg.rows // 2
                and tb in dist):
            goal = tb
        else:
            toward = [b for b in dist if b != start]
            if not toward:
                return None
            goal = min(toward, key=lambda b: (abs(b[0] - tb[0])
                                              + abs(b[1] - tb[1]), dist[b]))
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
        if count is None:
            # STRAIGHT STRIDE (user design 2026-07-21, after the forest maze
            # laps): a plain walk_<dir> goes EXACTLY that way until a wall
            # stops it — no BFS toward "farthest reachable", which routed
            # around trees and landed the player south-east of a walk_north
            # (the (1,30)->(6,34) confusion). The outcome now matches the
            # ask, and where the stride STOPS is a boundary the model can
            # reason about. Two faithful exceptions, both reported by the
            # motion itself: a single-block obstacle is sidestepped when one
            # lateral step reopens the ray (a lone tree must not end a
            # stride), and striding DOWN over a hoppable ledge hops it.
            btn_of = {(0, -1): "UP", (0, 1): "DOWN",
                      (-1, 0): "LEFT", (1, 0): "RIGHT"}
            dxy = (sign, 0) if axis == 0 else (0, sign)
            fwd_btn = btn_of[dxy]
            cols_b, rows_b = cfg.cols // 2, cfg.rows // 2

            def _open(b: tuple[int, int]) -> bool:
                return (0 <= b[0] < cols_b and 0 <= b[1] < rows_b
                        and grid[b[1]][b[0]])

            # while walking the ray, ENUMERATE the perpendicular openings it
            # passes — a stride glides straight past a one-block gap in a
            # parallel wall, and the model cannot spot a lone "." in a grid
            # of "#" (same lesson as the warp "Exits:" summary line). The
            # note reports each passage's side + distance in the same step
            # units bearings use, so it plugs into the existing counted-walk
            # drill ("east after 3" -> walk_north_3, walk_east).
            side_name = {(-dxy[1], dxy[0]): btn_of[(-dxy[1], dxy[0])],
                         (dxy[1], -dxy[0]): btn_of[(dxy[1], -dxy[0])]}
            word = {"UP": "north", "DOWN": "south",
                    "LEFT": "west", "RIGHT": "east"}
            passages: list[tuple[str, int]] = []
            last_open: dict[str, bool] = {}
            stride: list[str] = []
            cur = start
            fwd_count = 0  # forward steps only — the distance the note reports

            def _scan_sides() -> None:
                for sv, btn in side_name.items():
                    is_open = _open((cur[0] + sv[0], cur[1] + sv[1]))
                    # a multi-block gap is ONE passage, reported at entry
                    if is_open and not last_open.get(btn, False) \
                            and fwd_count > 0 and len(passages) < 6:
                        passages.append((word[btn], fwd_count))
                    last_open[btn] = is_open

            _scan_sides()  # seed adjacency so a gap at step 1 reports cleanly
            while len(stride) < MAX_STEPS:
                n = (cur[0] + dxy[0], cur[1] + dxy[1])
                if _open(n):
                    stride.append(fwd_btn)
                    cur = n
                    fwd_count += 1
                    _scan_sides()
                    continue
                if fwd_btn == "DOWN" and n in ledge_blocks:
                    n2 = (cur[0], cur[1] + 2)
                    if _open(n2):
                        stride.append("DOWN*")
                        cur = n2
                        fwd_count += 2
                        _scan_sides()
                        continue
                stepped = False
                if len(stride) + 2 <= MAX_STEPS:
                    sides = [(-dxy[1], dxy[0]), (dxy[1], -dxy[0])]
                    random.shuffle(sides)
                    for sx, sy in sides:
                        s = (cur[0] + sx, cur[1] + sy)
                        s2 = (s[0] + dxy[0], s[1] + dxy[1])
                        if _open(s) and _open(s2):
                            stride.append(btn_of[(sx, sy)])
                            stride.append(fwd_btn)
                            cur = s2
                            fwd_count += 1
                            last_open.clear()  # lateral shift: re-seed sides
                            _scan_sides()
                            stepped = True
                            break
                if not stepped:
                    break  # a real wall: the stride ends here, honestly
            if stride:
                went = word[fwd_btn]
                hit_cap = len(stride) >= MAX_STEPS
                nxt = (cur[0] + dxy[0], cur[1] + dxy[1])
                off_screen = not (0 <= nxt[0] < cols_b and 0 <= nxt[1] < rows_b)
                # a door tile reads as a stride-stopper too - but calling it
                # "a wall" contradicts the can_move line's "through a
                # doorway" and the model must not have to reconcile that
                door_ahead = False
                if player is not None and warps:
                    wb = {((cfg.player_col + (wx - px) * 2) // 2,
                           (cfg.player_row + (wy - py) * 2) // 2)
                          for wx, wy in warps}
                    door_ahead = nxt in wb
                # honest endings: budget spent (say nothing), the visible
                # window ran out (the world continues - walking again shows
                # more), a doorway (one press steps through), or a wall
                note = f"[walk_{went}: went {fwd_count}" + \
                       ("" if hit_cap else
                        ", edge of sight - walk again to see further"
                        if off_screen else
                        ", stopped at a DOORWAY - one single press that "
                        "way steps through it"
                        if door_ahead else ", stopped at a wall")
                if passages:
                    note += "; openings passed: " + ", ".join(
                        f"{side} after {d}" for side, d in passages)
                note += "]"
                return Behavior(name=orig, source="builtin", note=note,
                                steps=[Step(button=d.rstrip("*"),
                                            hold_frames=8,
                                            wait_frames=30 if d.endswith("*")
                                            else 8)
                                       for d in stride])
            # blocked on the very first block: fall through to the single
            # direct press below (edge crossings + honest "[move blocked]")
        else:
            # counted variants stay BFS-exact: they pair with bearings
            # ("3 south, 4 east"), where routed precision is the point
            cands = [b for b in dist
                     if b != start and 0 < sign * (b[axis] - start[axis])
                     and sign * (b[axis] - start[axis]) <= count]
            if cands:
                goal = min(cands,
                           key=lambda b: (-sign * (b[axis] - start[axis]),
                                          dist[b]))
    if goal is None:
        if name not in ("walk_to_exit", "walk_to_counter", "walk_to_mark"):
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
