from dataclasses import dataclass, field, fields
from enum import StrEnum
from typing import Any

from mashumaro import DataClassDictMixin
from mashumaro.config import BaseConfig
from mashumaro.types import Discriminator


class LightLayerType(StrEnum):
    SOLID = "solid"
    RADIAL_PULSE = "radial_pulse"
    WIPE = "wipe"
    BLINK = "blink"
    CHASE = "chase"
    SPARKLE = "sparkle"


@dataclass
class LightLayerDef(DataClassDictMixin):
    type: LightLayerType
    name: str = field(default="Layer", metadata={"editor": "text"})
    start_ms: int = field(default=0, metadata={"editor": "int", "min": 0, "max": 10_000_000})
    duration_ms: int = field(default=1000, metadata={"editor": "int", "min": 1, "max": 10_000_000})
    color: str = field(default="#ffffff", metadata={"editor": "color"})
    intensity: float = field(default=1.0, metadata={"editor": "float", "min": 0.0, "max": 1.0, "step": 0.05})

    class Config(BaseConfig):
        forbid_extra_keys = False
        discriminator = Discriminator(
            field="type",
            include_subtypes=True,
        )


@dataclass
class SolidLayerDef(LightLayerDef):
    type: LightLayerType = field(default=LightLayerType.SOLID, metadata={"editor": "layer_type"})


@dataclass
class RadialPulseLayerDef(LightLayerDef):
    type: LightLayerType = field(default=LightLayerType.RADIAL_PULSE, metadata={"editor": "layer_type"})

    center: list[float] = field(
        default_factory=lambda: [0.5, 0.5],
        metadata={"editor": "point2", "min": 0.0, "max": 1.0, "step": 0.01},
    )
    radius_from: float = field(default=0.0, metadata={"editor": "float", "min": 0.0, "max": 10.0, "step": 0.01})
    radius_to: float = field(default=0.5, metadata={"editor": "float", "min": 0.0, "max": 10.0, "step": 0.01})
    width: float = field(default=0.15, metadata={"editor": "float", "min": 0.0, "max": 10.0, "step": 0.01})


@dataclass
class WipeLayerDef(LightLayerDef):
    type: LightLayerType = field(default=LightLayerType.WIPE, metadata={"editor": "layer_type"})

    direction: list[float] = field(
        default_factory=lambda: [1.0, 0.0],
        metadata={"editor": "point2", "min": -1.0, "max": 1.0, "step": 0.05},
    )
    width: float = field(default=0.15, metadata={"editor": "float", "min": 0.0, "max": 10.0, "step": 0.01})
    speed: float = field(default=1.0, metadata={"editor": "float", "min": 0.0, "max": 100.0, "step": 0.05})


@dataclass
class BlinkLayerDef(LightLayerDef):
    type: LightLayerType = field(default=LightLayerType.BLINK, metadata={"editor": "layer_type"})

    speed: float = field(default=1.0, metadata={"editor": "float", "min": 0.0, "max": 100.0, "step": 0.05})


@dataclass
class ChaseLayerDef(LightLayerDef):
    type: LightLayerType = field(default=LightLayerType.CHASE, metadata={"editor": "layer_type"})

    width: float = field(default=0.15, metadata={"editor": "float", "min": 0.0, "max": 10.0, "step": 0.01})
    speed: float = field(default=1.0, metadata={"editor": "float", "min": 0.0, "max": 100.0, "step": 0.05})
    led_count: int = field(default=1, metadata={"editor": "int", "min": 1, "max": 9999})


@dataclass
class SparkleLayerDef(LightLayerDef):
    type: LightLayerType = field(default=LightLayerType.SPARKLE, metadata={"editor": "layer_type"})

    seed: int = field(default=1, metadata={"editor": "int", "min": 0, "max": 2_147_483_647})
    density: float = field(default=0.2, metadata={"editor": "float", "min": 0.0, "max": 1.0, "step": 0.05})
    speed: float = field(default=1.0, metadata={"editor": "float", "min": 0.0, "max": 100.0, "step": 0.05})


LAYER_CLASSES_BY_TYPE: dict[str, type[LightLayerDef]] = {
    "solid": SolidLayerDef,
    "radial_pulse": RadialPulseLayerDef,
    "wipe": WipeLayerDef,
    "blink": BlinkLayerDef,
    "chase": ChaseLayerDef,
    "sparkle": SparkleLayerDef,
}


def normalize_layer_dict(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    return normalized


def layer_from_dict(data: dict[str, Any]) -> LightLayerDef:
    normalized = normalize_layer_dict(data)
    layer_type = str(normalized.get("type", "solid"))
    return LAYER_CLASSES_BY_TYPE[layer_type].from_dict(normalized)


def convert_layer_type(layer: LightLayerDef, new_type: str | LightLayerType) -> LightLayerDef:
    type_value = str(new_type.value if isinstance(new_type, LightLayerType) else new_type)
    layer_cls = LAYER_CLASSES_BY_TYPE[type_value]

    old_data = layer.to_dict()
    old_data["type"] = type_value

    allowed = {
        field_def.name
        for field_def in fields(layer_cls)
        if field_def.init
    }

    new_data = {
        key: value
        for key, value in old_data.items()
        if key in allowed
    }

    return layer_cls.from_dict(new_data)
