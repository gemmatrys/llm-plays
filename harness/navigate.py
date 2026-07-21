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

from collections import deque

from .tilemap import _map_coord
from .types import Behavior, Step

NAV_BEHAVIORS = ("walk_north", "walk_south", "walk_west", "walk_east",
                 "walk_to_exit")
MAX_STEPS = 12  # re-decide after ~a screen's worth of walking

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
            ledges: set[int] = frozenset()) -> Behavior | None:
    """Turn a navigation behavior name into a concrete button path, or None
    when no on-screen path exists (caller reports that to the model)."""
    if name not in NAV_BEHAVIORS or not walkable:
        return None
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
            return Behavior(name=name, source="builtin",
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
    if name == "walk_to_exit":
        cands = [(dist[b], b) for b in warp_blocks if b in dist and b != start]
        if cands:
            goal = min(cands)[1]
        elif warps and player is not None:
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
                 if b != start and sign * (b[axis] - start[axis]) > 0]
        if cands:
            # farthest progress along the axis, shortest path as tiebreak
            goal = min(cands, key=lambda b: (-sign * (b[axis] - start[axis]),
                                             dist[b]))
    if goal is None:
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
    return Behavior(name=name, source="builtin", steps=steps)
