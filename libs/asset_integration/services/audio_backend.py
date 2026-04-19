from __future__ import annotations

from typing import Protocol


class AudioBackend(Protocol):
    def preload(self, clip_name: str, path: str) -> None:
        ...

    def play(
        self,
        clip_name: str,
        path: str,
        *,
        mode: str,
        interrupt: str,
        channel: str | None,
        gain: float,
    ) -> None:
        ...

    def stop(
        self,
        *,
        clip_name: str | None = None,
        channel: str | None = None,
    ) -> None:
        ...

    def stop_all(self) -> None:
        ...
