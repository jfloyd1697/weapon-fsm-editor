from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AudioMode = Literal["one_shot", "loop"]
AudioInterruptMode = Literal["restart", "ignore", "schedule"]
LightMode = Literal["one_shot", "loop"]


@dataclass(frozen=True)
class GunRuntimeCommand:
    pass


@dataclass(frozen=True)
class PlayAudioCommand(GunRuntimeCommand):
    clip_name: str
    resolved_path: str
    mode: AudioMode = "one_shot"
    interrupt: AudioInterruptMode = "restart"
    channel: str | None = None
    gain: float = 1.0


@dataclass(frozen=True)
class StopAudioCommand(GunRuntimeCommand):
    clip_name: str | None = None
    channel: str | None = None


@dataclass(frozen=True)
class PlayLightCommand(GunRuntimeCommand):
    sequence_name: str
    resolved_path: str
    mode: LightMode = "one_shot"
    target: str | None = None


@dataclass(frozen=True)
class StopLightCommand(GunRuntimeCommand):
    sequence_name: str | None = None
    target: str | None = None
