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
    # Alerting: escalations are otherwise just records — this command is
    # launched detached on EVERY escalation (any kind, cooldown-guarded),
    # with context in LLMPLAYS_KIND/DETAIL/SNAPSHOT/RUN env vars. Wire it to
    # a toast, a webhook, or a headless Claude checkpoint.
    alert_cmd: list[str] | None = None
    alert_cooldown_s: float = 300.0


@dataclass
class TilemapConfig:
    """On-screen tile grid -> ASCII walkability map for the model. addr/cols/rows
    are solid (Gen 1 wTileMap is a 20x18 WRAM buffer at 0xC3A0). player_col/row
    are GAME-SPECIFIC and must be confirmed against a LIVE overworld screen.

    Walkability is PER-TILESET (indoor rooms reuse ids the overworld treats as
    open — floor 0x01 vs wall 0x00 collide exactly backwards): populate
    `walkable_by_tileset` keyed by the tileset id read from `tileset_addr`. A
    tileset with no entry (or an empty `walkable` when no by-tileset table is
    configured) makes the renderer fall back to raw tile ids — which is also
    how you harvest the ids for a new tileset's entry."""
    addr: int                      # wTileMap start (0xC3A0 for Gen 1)
    cols: int = 20
    rows: int = 18
    player_col: int = 8            # player's on-screen tile column
    player_row: int = 8            # player's on-screen tile row
    scale: int = 2                 # screen tiles per map tile (Gen 1 blocks are 2x2)
    window: int = 4                # render a (2*window+1) box around player; 0 = full
    walkable: list[int] = field(default_factory=list)  # legacy single set (all tilesets)
    tileset_addr: int = 0xD367     # wCurMapTileset
    # tileset id -> passable tile ids; missing tileset = raw-id dump
    walkable_by_tileset: dict[int, list[int]] = field(default_factory=dict)
    # preferred: HOT-loaded per-tileset terrain map (walkable + portal ids,
    # block bottom-left convention) — see harness/tilemap.py TerrainTable.
    # Checkpoints edit it live; walkable_by_tileset above is the fallback.
    tiles_file: str | None = None
    # sprite table (Gen 1 wSpriteStateData1): people/NPCs rendered as N on the
    # map — they block movement but are invisible in the tile data
    sprites_addr: int = 0xC100
    sprites_count: int = 16
    # map dimensions (blocks; x2 = tiles) so off-map tiles render blocked
    height_addr: int = 0xD368      # wCurMapHeight
    width_addr: int = 0xD369       # wCurMapWidth
    # warps = doors/stairs/holes; count then 4-byte entries (y, x, destWarp, destMap)
    warp_count_addr: int = 0xD3AE  # wNumberOfWarps
    warp_entry_addr: int = 0xD3AF  # wWarpEntries
    # (bag lives in its own config on GameProfile — see BagConfig)
    # dialogue state, for the executor's closed-loop text advance
    # (op "advance_text"): font_addr bit 0 is set while a text box is open
    # (wFontLoaded — verified live 2026-07-20: 1 through the whole nurse
    # dialogue, 0 in the overworld); menu_cursor_tile is the ▶ selection
    # glyph drawn whenever a choice menu is up — its presence anywhere on
    # screen means "stop, the model must answer".
    font_addr: int = 0xCFC4        # wFontLoaded
    menu_cursor_tile: int = 0xED   # ▶
    max_text_presses: int = 12
    # battles never set wFontLoaded (live-verified: font=0 with EXP text on
    # screen), so in battle advance_text presses A until the menu cursor
    # appears or the battle ends instead of consulting the font flag
    battle_addr: int | None = 0xD057  # wIsInBattle


@dataclass
class BagConfig:
    """Game-verified inventory: count byte + (id, qty) pairs (Gen 1 layout).
    Rendered into the model's {ram} view as `bag=` and diffed into
    "[bag: +N ITEM]" events — the ground-truth spine that self-narrated
    events ("I delivered it") lack. Names come from a HOT yaml harvested by
    checkpoints (unknown ids show as ITEM_0xXX)."""
    count_addr: int = 0xD31D       # wNumBagItems
    items_addr: int = 0xD31E       # wBagItems
    max_items: int = 20
    names_file: str | None = None  # data/<game>/items.yaml


@dataclass
class PartyConfig:
    """Party state for the model's {ram} view (`party=`): nickname, species,
    level, HP, status per mon — the model must SEE low HP and poison to
    decide to heal. Gen 1 layout, offsets live-verified 2026-07-20
    (species 0xB0 lv8 HP16/24 nick 'A' read back correctly)."""
    count_addr: int = 0xD163       # wPartyCount
    species_addr: int = 0xD164     # wPartySpecies (0xFF-terminated)
    mons_addr: int = 0xD16B        # wPartyMons: 44-byte structs
    mon_size: int = 44
    hp_off: int = 1                # current HP, 2 bytes big-endian
    status_off: int = 4
    level_off: int = 33
    maxhp_off: int = 34            # 2 bytes big-endian
    nicks_addr: int = 0xD2B5       # wPartyMonNicks: 11 bytes each
    nick_size: int = 11
    moves_off: int = 8             # 4 move ids (0 = empty slot)
    pp_off: int = 29               # 4 PP bytes; top 2 bits are PP-Up count
    moves_file: str | None = None  # id -> display name (data/<game>/moves.yaml)
    names_file: str | None = None  # data/<game>/species.yaml


@dataclass
class BattleConfig:
    """Battle hint: enemy species/level/HP/types from the enemy battle
    struct + the Gen 1 type chart -> a computed `battle_hint=` line.
    Enemy struct mirrors the battle_struct layout (species, HP, boxlevel,
    status, type1, type2, catch, moves, DVs, level at +14, maxHP +15)."""
    enemy_addr: int = 0xCFE5       # wEnemyMon
    hp_off: int = 1                # 2 bytes big-endian
    type1_off: int = 5
    type2_off: int = 6
    level_off: int = 14
    maxhp_off: int = 15            # 2 bytes big-endian
    types_file: str | None = None  # data/<game>/types.yaml


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
    # extra RAM shown to the MODEL only (merged into its {ram} view) but NOT
    # milestone-tracked — e.g. in_battle, whose flapping must not spam metrics
    context_ram_map: dict[str, int] = field(default_factory=dict)
    tilemap: TilemapConfig | None = None
    bag: BagConfig | None = None
    party: PartyConfig | None = None
    battle: BattleConfig | None = None
    driver_opts: dict = field(default_factory=dict)
    # Gemma-facing prompts are NOT part of the profile — see harness/prompts.py.
    # Profiles are COLD config: loaded once at startup; changing one requires
    # tearing down the harness and starting a new run segment.
    skills_dirs: list[str] = field(default_factory=lambda: ["skills/common"])

    @classmethod
    def load(cls, path: str | Path) -> "GameProfile":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        _hex = lambda v: int(v, 0) if isinstance(v, str) else v  # noqa: E731
        for key, sub in (("ladder", LadderConfig), ("ratchet", RatchetConfig),
                         ("escalation", EscalationConfig)):
            if key in raw:
                raw[key] = sub(**raw[key])
        if raw.get("bag"):
            bg = dict(raw["bag"])
            for k in ("count_addr", "items_addr"):
                if k in bg:
                    bg[k] = _hex(bg[k])
            raw["bag"] = BagConfig(**bg)
        if raw.get("party"):
            pt = dict(raw["party"])
            for k in ("count_addr", "species_addr", "mons_addr", "nicks_addr"):
                if k in pt:
                    pt[k] = _hex(pt[k])
            raw["party"] = PartyConfig(**pt)
        if raw.get("battle"):
            bt = dict(raw["battle"])
            if "enemy_addr" in bt:
                bt["enemy_addr"] = _hex(bt["enemy_addr"])
            raw["battle"] = BattleConfig(**bt)
        # RAM addresses in YAML may be hex strings
        raw["ram_map"] = {k: int(v, 0) if isinstance(v, str) else v
                          for k, v in raw.get("ram_map", {}).items()}
        raw["context_ram_map"] = {k: int(v, 0) if isinstance(v, str) else v
                                  for k, v in raw.get("context_ram_map", {}).items()}
        if raw.get("tilemap"):
            tm = dict(raw["tilemap"])
            tm["addr"] = _hex(tm["addr"])
            tm["walkable"] = [_hex(v) for v in tm.get("walkable", [])]
            if "tileset_addr" in tm:
                tm["tileset_addr"] = _hex(tm["tileset_addr"])
            tm["walkable_by_tileset"] = {
                _hex(k): [_hex(v) for v in vs]
                for k, vs in tm.get("walkable_by_tileset", {}).items()}
            raw["tilemap"] = TilemapConfig(**tm)
        return cls(**raw)
