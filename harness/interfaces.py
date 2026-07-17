"""The seams: Eyes / Hands / Extras / Policy.

Every platform (mGBA, melonDS, capture-card+Pico, ...) implements Eyes and Hands.
Extras is nullable — real consoles raise Unsupported and callers must degrade.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import Behavior, Frame, Observation


class Unsupported(RuntimeError):
    """Raised by Extras methods a driver cannot provide (e.g. RAM reads on console)."""


@runtime_checkable
class Eyes(Protocol):
    def get_frame(self) -> Frame: ...


@runtime_checkable
class Hands(Protocol):
    def press(self, button: str, hold_frames: int) -> None: ...

    def key_down(self, button: str) -> None:
        """Hold a button until key_up. Drivers must support overlapping holds."""
        ...

    def key_up(self, button: str) -> None: ...

    def hard_reset(self) -> None: ...


class Extras(Protocol):
    def read_ram(self, ram_map: dict[str, int]) -> dict[str, int]:
        """Return {name: value} for each named address. May raise Unsupported."""
        ...

    def savestate(self, slot: int) -> None: ...

    def loadstate(self, slot: int) -> None: ...


class Policy(Protocol):
    """A decision source. Returns one Behavior or an ordered plan of them
    (or raises); the watchdog validates, truncates, and handles failure."""

    name: str

    def decide(self, obs: Observation) -> Behavior | list[Behavior]: ...
