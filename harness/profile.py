"""Game profile: the per-game YAML config that makes new games config, not code."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LadderConfig:
    # rung-2 behavior name(s). A list cycles one entry per fallback invocation:
    # a single behavior can't fit every context (mash_a is right in dialogue,
    # useless facing a wall), but a movement+interact rotation progresses both.
    scripted_fallback: str | list[str] = "mash_a"
    safe_idle: str = "wait"  # rung-3 behavior name
    allow_random: bool = True  # rung 4 permitted? (the fish clause)
    llm_timeout_s: float = 20.0  # rung-1 patience
    demote_after_failures: int = 3  # consecutive rung-1 failures before demotion
    promote_after_successes: int = 5  # successes at low rung before retrying rung 1
    max_plan_len: int = 8  # longest behavior plan one LLM call may emit
    plan_abort_pct: float = 0.4  # frame-hash change between steps that cancels a plan


@dataclass
class RatchetConfig:
    interval_s: float = 300.0  # max time between enforced saves
    savestate_slot: int = 1
    ingame_save_behavior: str | None = None  # console path: scripted in-game save


@dataclass
class EscalationConfig:
    # Detector thresholds (seconds; <= 0 disables that detector) — see
    # harness/stuckness.py for what each one catches and misses.
    stagnant_after_s: float = 1200.0  # screen: no novel phash for this long
    pos_stagnant_after_s: float = 900.0  # position: pinned in a tiny box, no RAM progress
    pos_box_tiles: int = 2  # "pinned" = within this many tiles of the anchor
    behavior_stagnant_after_s: float = 600.0  # behavior loop while position pinned
    behavior_distinct_max: int = 3  # "loop" = at most this many distinct behaviors
    milestone_stagnant_after_s: float = 7200.0  # no badge/map/party change at all
    # Staged response: one bounded random-input burst first (requires
    # ladder.allow_random), Claude escalation only if signals persist.
    self_rescue: bool = True
    rescue_grace_s: float = 300.0  # how long a rescue gets to show progress
    max_wakes_per_window: int = 2  # Claude-budget guard
    window_s: float = 18000.0  # 5 h


@dataclass
class TilemapConfig:
    """On-screen tile grid -> ASCII walkability map for the model. addr/cols/rows
    are solid (Gen 1 wTileMap is a 20x18 WRAM buffer at 0xC3A0). player_col/row
    and `walkable` are GAME-SPECIFIC and must be confirmed against a LIVE
    overworld screen — they're seeded with best-known Gen 1 values, not verified.
    An empty `walkable` list makes the renderer fall back to raw tile ids."""
    addr: int                      # wTileMap start (0xC3A0 for Gen 1)
    cols: int = 20
    rows: int = 18
    player_col: int = 8            # player's on-screen tile column
    player_row: int = 8            # player's on-screen tile row
    scale: int = 2                 # screen tiles per map tile (Gen 1 blocks are 2x2)
    window: int = 4                # render a (2*window+1) box around player; 0 = full
    walkable: list[int] = field(default_factory=list)  # passable tile ids (per tileset)
    # map dimensions (blocks; x2 = tiles) so off-map tiles render blocked
    height_addr: int = 0xD368      # wCurMapHeight
    width_addr: int = 0xD369       # wCurMapWidth
    # warps = doors/stairs/holes; count then 4-byte entries (y, x, destWarp, destMap)
    warp_count_addr: int = 0xD3AE  # wNumberOfWarps
    warp_entry_addr: int = 0xD3AF  # wWarpEntries


@dataclass
class GameProfile:
    name: str
    platform: str  # gba | gb | nds | switch ...
    driver: str  # mgba | capture_pico | ...
    rom: str | None
    buttons: list[str]
    decision_cadence_s: float = 3.0
    ladder: LadderConfig = field(default_factory=LadderConfig)
    ratchet: RatchetConfig = field(default_factory=RatchetConfig)
    escalation: EscalationConfig = field(default_factory=EscalationConfig)
    ram_map: dict[str, int] = field(default_factory=dict)
    tilemap: TilemapConfig | None = None
    driver_opts: dict = field(default_factory=dict)
    # Gemma-facing prompts are NOT part of the profile — see harness/prompts.py.
    # Profiles are COLD config: loaded once at startup; changing one requires
    # tearing down the harness and starting a new run segment.
    skills_dirs: list[str] = field(default_factory=lambda: ["skills/common"])

    @classmethod
    def load(cls, path: str | Path) -> "GameProfile":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        for key, sub in (("ladder", LadderConfig), ("ratchet", RatchetConfig),
                         ("escalation", EscalationConfig)):
            if key in raw:
                raw[key] = sub(**raw[key])
        # RAM addresses in YAML may be hex strings
        raw["ram_map"] = {k: int(v, 0) if isinstance(v, str) else v
                          for k, v in raw.get("ram_map", {}).items()}
        if raw.get("tilemap"):
            tm = dict(raw["tilemap"])
            _hex = lambda v: int(v, 0) if isinstance(v, str) else v  # noqa: E731
            tm["addr"] = _hex(tm["addr"])
            tm["walkable"] = [_hex(v) for v in tm.get("walkable", [])]
            raw["tilemap"] = TilemapConfig(**tm)
        return cls(**raw)
