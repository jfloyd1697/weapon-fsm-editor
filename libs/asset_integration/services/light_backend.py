from __future__ import annotations

from typing import Protocol


class LightBackend(Protocol):
    def preload(self, sequence_name: str, path: str) -> None:
        ...

    def play(
        self,
        sequence_name: str,
        path: str,
        *,
        mode: str,
        target: str | None,
    ) -> None:
        ...

    def stop(
        self,
        *,
        sequence_name: str | None = None,
        target: str | None = None,
    ) -> None:
        ...

    def stop_all(self) -> None:
        ...
