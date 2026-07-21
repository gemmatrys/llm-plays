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

Walkability is judged the way THE GAME judges it: per 2x2-tile BLOCK, by the
block's bottom-left subtile id (Gen 1 collision convention — pokered's
per-tileset collision lists are bottom-left ids). Classifying each 8x8
subtile independently renders mixed blocks wrong: overworld flower ground is
2c/03 mixed and produced a checkerboard of phantom walls until this fix.

Per-tileset terrain lives in a TerrainTable (data/<game>/tiles.yaml): each
tileset's walkable ids plus optional `portal` ids (door mats / stairs /
cave mouths) that render as `D` alongside the warp-table overlay. The file
is HOT: edited by checkpoints as new tilesets are harvested, reloaded on
mtime change, last-good kept on a parse error.
"""
from __future__ import annotations

from pathlib import Path

import yaml


def _hex(v) -> int:
    return int(v, 0) if isinstance(v, str) else int(v)


class TerrainTable:
    """Hot-loaded per-tileset terrain map. Missing file/tileset -> empty sets
    (renderer falls back to the raw-id dump, the harvesting view)."""

    def __init__(self, path: str | Path | None):
        self.path = Path(path) if path else None
        self.error: str | None = None
        self._mtime: float | None = None
        self._walkable: dict[int, set[int]] = {}
        self._portal: dict[int, set[int]] = {}

    def lookup(self, tileset: int) -> tuple[set[int], set[int]]:
        """(walkable ids, portal ids) for a tileset — block bottom-left ids."""
        self._refresh()
        return (self._walkable.get(tileset, set()),
                self._portal.get(tileset, set()))

    def _refresh(self) -> None:
        if self.path is None or not self.path.is_file():
            return
        mtime = self.path.stat().st_mtime
        if mtime == self._mtime:
            return
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
            walkable, portal = {}, {}
            for key, entry in (raw.get("tilesets") or {}).items():
                ts = _hex(key)
                walkable[ts] = {_hex(v) for v in entry.get("walkable", [])}
                portal[ts] = {_hex(v) for v in entry.get("portal", [])}
            self._walkable, self._portal = walkable, portal
            self._mtime = mtime
            self.error = None
        except Exception as e:  # noqa: BLE001 — keep last good table
            self.error = repr(e)


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
                 tileset: int | None = None,
                 portal_ids: "set[int] | None" = None) -> str:
    """Format `tiles` as an ASCII map windowed around the player. `player` is the
    map (x,y); `map_wh` the map (width,height) in tiles; `warps` a list of map
    (x,y) portal tiles; `tileset` the current tileset id, shown in the raw-dump
    header so logged dumps are attributable when harvesting a new tileset;
    `portal_ids` tile-id portals (door mats/stairs) rendered D like warps.
    Never raises on shape mismatch."""
    cols, rows = cfg.cols, cfg.rows
    if len(tiles) < cols * rows:
        return "(tilemap unavailable)"
    pc, pr, win = cfg.player_col, cfg.player_row, cfg.window
    c0, c1 = (0, cols) if win <= 0 else (max(0, pc - win), min(cols, pc + win + 1))
    r0, r1 = (0, rows) if win <= 0 else (max(0, pr - win), min(rows, pr + win + 1))
    walkable = set(cfg.walkable)
    portal_ids = portal_ids or set()
    warpset = set(warps or [])
    have_map = player is not None
    px, py = player if have_map else (0, 0)
    mw, mh = map_wh if map_wh else (None, None)

    def block_bl(c: int, r: int) -> int:
        # the game's collision convention: a 16x16 block is classified by its
        # BOTTOM-LEFT 8x8 subtile (blocks align to even screen coords)
        return tiles[min(r | 1, rows - 1) * cols + (c & ~1)]

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
            elif block_bl(c, r) in portal_ids:
                cells.append("D")
            else:
                cells.append("." if block_bl(c, r) in walkable else "#")
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
