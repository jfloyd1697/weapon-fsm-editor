from __future__ import annotations

from typing import Protocol


class AudioBackend(Protocol):
    def play_audio(
        self,
        *,
        clip: str,
        path: str,
        mode: str,
        interrupt: str,
    ) -> None:
        print(vars())

    def stop_audio(self) -> None:
        print(vars())


class LightBackend(Protocol):
    def play_light(
        self,
        *,
        sequence: str,
        path: str,
        mode: str,
    ) -> None: ...

    def stop_light(self) -> None:
        print(vars())
