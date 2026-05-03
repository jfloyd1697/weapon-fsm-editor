from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from mashumaro import DataClassDictMixin

from weapon_fsm_lights.domain.animation_layers import LightLayerDef


class LightAnimationMode(StrEnum):
    ONCE = "once"
    LOOP = "loop"


@dataclass
class LightAnimationDef(DataClassDictMixin):
    name: str = ""
    frame_duration_ms: int = 33
    duration_ms: int = 1000
    mode: LightAnimationMode = LightAnimationMode.ONCE
    layers: list[LightLayerDef] = field(default_factory=list)


@dataclass
class LightAnimationProject(DataClassDictMixin):
    layout: dict[str, Any] = field(default_factory=dict)
    animations: dict[str, LightAnimationDef] = field(default_factory=dict)

    @classmethod
    def __pre_deserialize__(cls, value: dict[str, Any]) -> dict[str, Any]:
        data = dict(value)

        normalized_animations: dict[str, dict[str, Any]] = {}

        for animation_name, raw_animation in data.get("animations", {}).items():
            animation_data = dict(raw_animation)
            animation_data.setdefault("name", str(animation_name))
            normalized_animations[str(animation_name)] = animation_data

        data["animations"] = normalized_animations
        return data