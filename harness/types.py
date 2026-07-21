"""Core data types shared across the harness."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from PIL import Image


class Rung(IntEnum):
    """Fallback ladder rungs. Lower value = more trusted."""

    LLM = 1
    SCRIPTED = 2
    SAFE_IDLE = 3
    RANDOM = 4


@dataclass
class Frame:
    image: Image.Image
    ts: float = field(default_factory=time.time)

    def phash(self, size: int = 16) -> str:
        """Cheap perceptual hash: grayscale, downsample, threshold on mean.

        Used for stuckness detection — two frames with the same phash are
        'the same screen' for stagnation purposes.
        """
        img = self.image.convert("L").resize((size, size), Image.BILINEAR)
        px = list(img.getdata())
        mean = sum(px) / len(px)
        bits = "".join("1" if p > mean else "0" for p in px)
        return f"{int(bits, 2):0{size * size // 4}x}"


@dataclass
class Observation:
    """Everything a policy gets to see when deciding."""

    frame: Frame
    ram: dict[str, int] | None  # named values per profile ram_map; None on console
    goals: str  # current goals.md content
    recent: list[str]  # last few behavior names executed
    memory: str = ""  # the model's OWN notes, carried verbatim between decisions
    tilemap: str = ""  # ASCII walkability map around the player (may be empty)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Step:
    """One executor step.

    - button set, op None: press-and-release (held hold_frames, then wait_frames)
    - op "keydown"/"keyup" + button: explicit press/release, for combos and holds
      (any key still down when the behavior ends is auto-released by the executor)
    - op "wait": idle wait_frames
    - op "savestate": ratchet save
    """

    button: str | None = None
    hold_frames: int = 8
    wait_frames: int = 4
    op: str | None = None  # "savestate" | "wait" | "keydown" | "keyup"


@dataclass
class Behavior:
    name: str
    steps: list[Step]
    source: str = "builtin"  # builtin | skill | llm | claude
    # optional: generate fresh steps at execute time (randomized/reflexive
    # behaviors). When set, the executor calls this instead of using `steps`.
    step_factory: Callable[[], list[Step]] | None = None


@dataclass
class Decision:
    """One watchdog verdict: an ordered plan of 1..N behaviors to execute.

    Multi-step plans amortize inference latency; the loop aborts remaining steps
    when the screen changes more than the profile's plan_abort_pct between steps.
    """

    behaviors: list[Behavior]
    rung: Rung
    reason: str = ""
    prompt_hash: str = ""  # which prompt.md version produced this (rung 1 only)
    memory_update: str | None = None  # model rewrote its notes (None = unchanged)
    done_goal: int | None = None  # model says numbered goal N is finished
    thinking: str = ""  # reasoning_content when thinking mode is on (truncated)


def phash_diff(a: str, b: str) -> float:
    """Fraction of differing bits between two phash hex strings (0.0–1.0)."""
    return bin(int(a, 16) ^ int(b, 16)).count("1") / (len(a) * 4)
