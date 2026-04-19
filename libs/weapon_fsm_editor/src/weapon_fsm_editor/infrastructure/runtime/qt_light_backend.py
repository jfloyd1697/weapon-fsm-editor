from __future__ import annotations

from typing import Callable


class QtLightBackend:
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        self._log = log or (lambda message: None)
        self._active_sequence: str | None = None

    def play_light(self, *, sequence: str, path: str, mode: str) -> None:
        self._active_sequence = sequence
        self._log(f"[light] play sequence={sequence} mode={mode} path={path}")

    def stop_light(self) -> None:
        if self._active_sequence is not None:
            self._log(f"[light] stop sequence={self._active_sequence}")
        self._active_sequence = None
