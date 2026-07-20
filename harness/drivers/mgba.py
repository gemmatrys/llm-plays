"""mGBA driver: Eyes + Hands + Extras over a TCP line protocol served by
emulator/mgba_bridge.lua running inside mGBA's scripting console.

Protocol (one command per line, one "OK ..." / "ERR ..." reply per line):
    PING                        -> OK PONG
    SCREENSHOT <abs-path>       -> OK <abs-path>     (Lua saves PNG to that path)
    PRESS <BUTTON> <frames>     -> OK                (held for N frames, frame-timed)
    DOWN <BUTTON>               -> OK                (held until UP)
    UP <BUTTON>                 -> OK
    READ8 <addr>                -> OK <value>
    SAVESTATE <slot>            -> OK
    LOADSTATE <slot>            -> OK
    RESET                       -> OK

NOTE: scaffold — exact mGBA Lua API names verified in Phase 0 on the real setup.
"""
from __future__ import annotations

import socket
import tempfile
import time
import uuid
from pathlib import Path

from PIL import Image

from ..interfaces import Unsupported
from ..types import Frame


class MGBADriver:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                 screenshot_dir: str | None = None, timeout_s: float = 5.0):
        self.host, self.port, self.timeout_s = host, port, timeout_s
        self.screenshot_dir = Path(screenshot_dir or tempfile.mkdtemp(prefix="mgba_"))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._sock: socket.socket | None = None
        self._buf = b""

    # -- transport ------------------------------------------------------------
    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), self.timeout_s)
        self._sock.settimeout(self.timeout_s)
        if self._cmd("PING") != "PONG":
            raise ConnectionError("mgba bridge did not answer PING")

    def _cmd(self, line: str) -> str:
        if self._sock is None:
            self.connect()
        try:
            self._sock.sendall(line.encode() + b"\n")
            while b"\n" not in self._buf:
                chunk = self._sock.recv(4096)
                if not chunk:
                    raise ConnectionError("mgba bridge closed the connection")
                self._buf += chunk
        except OSError:
            # drop the dead socket so the next command reconnects — an aborted
            # connection (emulator restarted) must not wedge the driver forever
            self._sock = None
            self._buf = b""
            raise
        reply, self._buf = self._buf.split(b"\n", 1)
        reply = reply.decode().strip()
        if reply.startswith("OK"):
            return reply[2:].strip()
        raise RuntimeError(f"mgba bridge error for {line!r}: {reply}")

    # -- Eyes -------------------------------------------------------------------
    def get_frame(self) -> Frame:
        path = self.screenshot_dir / f"{uuid.uuid4().hex}.png"
        self._cmd(f"SCREENSHOT {path.as_posix()}")
        deadline = time.time() + self.timeout_s
        while time.time() < deadline:  # Lua writes async on next frame
            try:
                img = Image.open(path)
                img.load()
                path.unlink(missing_ok=True)
                if img.size == (256, 224):
                    # Super Game Boy frame: the GB screen sits at (48,40);
                    # crop away the decorative border so the model (and
                    # phash) only ever see actual game pixels
                    img = img.crop((48, 40, 208, 184))
                return Frame(image=img)
            except (FileNotFoundError, OSError):
                time.sleep(0.02)
        raise TimeoutError("screenshot never appeared")

    # -- Hands --------------------------------------------------------------------
    def press(self, button: str, hold_frames: int) -> None:
        self._cmd(f"PRESS {button.upper()} {hold_frames}")

    def key_down(self, button: str) -> None:
        self._cmd(f"DOWN {button.upper()}")

    def key_up(self, button: str) -> None:
        self._cmd(f"UP {button.upper()}")

    def hard_reset(self) -> None:
        self._cmd("RESET")

    # -- Extras ---------------------------------------------------------------------
    def read_ram(self, ram_map: dict[str, int]) -> dict[str, int]:
        return {name: int(self._cmd(f"READ8 {addr:#x}")) for name, addr in ram_map.items()}

    def savestate(self, slot: int) -> None:
        self._cmd(f"SAVESTATE {slot}")

    def loadstate(self, slot: int) -> None:
        self._cmd(f"LOADSTATE {slot}")
