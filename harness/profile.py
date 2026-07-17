"""Game profile: the per-game YAML config that makes new games config, not code."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LadderConfig:
    scripted_fallback: str = "mash_a"  # rung-2 behavior name
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
    stagnant_after_s: float = 1200.0  # same-screen time that counts as stuck
    max_wakes_per_window: int = 2  # Claude-budget guard
    window_s: float = 18000.0  # 5 h


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
        return cls(**raw)
