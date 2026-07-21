"""Render the on-screen tile grid as a compact ASCII walkability map.

A small model reads a clean `.`/`#` grid far better than it reads a blurry
160x144 Game Boy frame, so this is the highest-value context lever for
navigation (PLAN 7.0.4 / 7.0.5, and the vision-quality risk in 9). The raw
tile bytes come from the driver's bulk read (`read_block`); this module only
formats them, plus two reliable RAM-derived overlays:

- off-map tiles (beyond the current map's width/height) render as blocked, so
  the model never thinks it can walk into the border void;
- warps (doors/stairs/holes, from the warp table) render as `D`, and a summary
  line gives each exit as a relative direction — this is how the model finds its
  way out of a room even when the tileset walkability is imperfect.
"""
from __future__ import annotations


def _map_coord(sc: int, sr: int, cfg, px: int, py: int) -> tuple[int, int]:
    """Screen tile (col,row) -> map tile (x,y). One map tile spans cfg.scale
    screen tiles (Gen 1 blocks are 2x2), and the player's map tile sits at
    (cfg.player_col, cfg.player_row)."""
    return px + (sc - cfg.player_col) // cfg.scale, py + (sr - cfg.player_row) // cfg.scale


def _exit_dir(dx: int, dy: int) -> str:
    parts = []
    if dy < 0:
        parts.append(f"{-dy} up")
    elif dy > 0:
        parts.append(f"{dy} down")
    if dx < 0:
        parts.append(f"{-dx} left")
    elif dx > 0:
        parts.append(f"{dx} right")
    return ", ".join(parts) if parts else "right here"


def render_ascii(tiles: bytes, cfg, player: tuple[int, int] | None = None,
                 map_wh: tuple[int, int] | None = None,
                 warps: list[tuple[int, int]] | None = None,
                 tileset: int | None = None) -> str:
    """Format `tiles` as an ASCII map windowed around the player. `player` is the
    map (x,y); `map_wh` the map (width,height) in tiles; `warps` a list of map
    (x,y) portal tiles; `tileset` the current tileset id, shown in the raw-dump
    header so logged dumps are attributable when harvesting a new tileset's
    walkable ids. Never raises on shape mismatch."""
    cols, rows = cfg.cols, cfg.rows
    if len(tiles) < cols * rows:
        return "(tilemap unavailable)"
    pc, pr, win = cfg.player_col, cfg.player_row, cfg.window
    c0, c1 = (0, cols) if win <= 0 else (max(0, pc - win), min(cols, pc + win + 1))
    r0, r1 = (0, rows) if win <= 0 else (max(0, pr - win), min(rows, pr + win + 1))
    walkable = set(cfg.walkable)
    warpset = set(warps or [])
    have_map = player is not None
    px, py = player if have_map else (0, 0)
    mw, mh = map_wh if map_wh else (None, None)

    lines = []
    for r in range(r0, r1):
        cells = []
        for c in range(c0, c1):
            if c == pc and r == pr:
                cells.append("P")
                continue
            mx, my = _map_coord(c, r, cfg, px, py) if have_map else (None, None)
            if have_map and (mx, my) in warpset:
                cells.append("D")
            elif mw is not None and (mx < 0 or mx >= mw or my < 0 or my >= mh):
                cells.append("#")                       # off-map border: blocked
            elif not walkable:
                cells.append(f"{tiles[r * cols + c]:02x}")
            else:
                cells.append("." if tiles[r * cols + c] in walkable else "#")
        lines.append(("" if walkable else " ").join(cells))

    head = ("Map around you - P=you, D=door/exit, .=open, #=blocked (north up):"
            if walkable else
            "On-screen tile ids (no walkable set"
            + (f" for tileset {tileset}" if tileset is not None else " configured")
            + "):")
    out = [head, "\n".join(lines)]
    if warps and have_map:
        on_exit = (px, py) in warpset
        dirs = "; ".join(_exit_dir(wx - px, wy - py) for wx, wy in warps)
        out.append(("You ARE standing on an exit." if on_exit
                    else "You are not on an exit.") + f" Exits: {dirs}.")
    return "\n".join(out)
