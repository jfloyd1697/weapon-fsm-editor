from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AudioMode = Literal["one_shot", "loop"]
AudioInterruptMode = Literal["restart", "ignore", "schedule"]
LightMode = Literal["one_shot", "loop"]


@dataclass(frozen=True)
class ActionDef:
    type: str


@dataclass(frozen=True)
class PlayAudioActionDef(ActionDef):
    clip: str
    mode: AudioMode = "one_shot"
    interrupt: AudioInterruptMode = "restart"
    channel: str | None = None
    gain: float | None = None

    def __init__(
        self,
        clip: str,
        mode: AudioMode = "one_shot",
        interrupt: AudioInterruptMode = "restart",
        channel: str | None = None,
        gain: float | None = None,
    ) -> None:
        object.__setattr__(self, "type", "play_audio")
        object.__setattr__(self, "clip", clip)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "interrupt", interrupt)
        object.__setattr__(self, "channel", channel)
        object.__setattr__(self, "gain", gain)


@dataclass(frozen=True)
class StopAudioActionDef(ActionDef):
    clip: str | None = None
    channel: str | None = None

    def __init__(self, clip: str | None = None, channel: str | None = None) -> None:
        object.__setattr__(self, "type", "stop_audio")
        object.__setattr__(self, "clip", clip)
        object.__setattr__(self, "channel", channel)


@dataclass(frozen=True)
class PlayLightActionDef(ActionDef):
    sequence: str
    mode: LightMode = "one_shot"
    target: str | None = None

    def __init__(self, sequence: str, mode: LightMode = "one_shot", target: str | None = None) -> None:
        object.__setattr__(self, "type", "play_light")
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "target", target)


@dataclass(frozen=True)
class StopLightActionDef(ActionDef):
    sequence: str | None = None
    target: str | None = None

    def __init__(self, sequence: str | None = None, target: str | None = None) -> None:
        object.__setattr__(self, "type", "stop_light")
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "target", target)
