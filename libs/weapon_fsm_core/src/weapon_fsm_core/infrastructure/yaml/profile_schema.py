from dataclasses import dataclass, field
from typing import Any, Dict

from mashumaro.mixins.dict import T
from mashumaro.mixins.yaml import DataClassYAMLMixin


@dataclass
class EventFile(DataClassYAMLMixin):
    id: str
    label: str | None = None
    kind: str = "external"


@dataclass
class ClipFile(DataClassYAMLMixin):
    path: str
    preload: bool = True


@dataclass
class LightSequenceFile(DataClassYAMLMixin):
    path: str
    preload: bool = True


@dataclass
class ClipSetFile(DataClassYAMLMixin):
    clips: list[str] = field(default_factory=list)
    mode: str = "random"


@dataclass
class ActionFile(DataClassYAMLMixin):
    type: str
    arguments: dict[str, Any] = field(default_factory=dict)
    sound: str | None = None
    clip: str | None = None
    clips: list[str] = field(default_factory=list)
    clip_set: str | None = None
    pattern: str | None = None
    sequence: str | None = None
    event: str | None = None
    delay_ms: int | None = None
    delta: int | None = None
    value: int | None = None
    interrupt: str | None = "interrupt"
    mode: str | None = "one_shot"

    @classmethod
    def __pre_deserialize__(cls, d: Dict[Any, Any]) -> Dict[Any, Any]:
        return {k: v for k, v in d.items() if v}

    def __post_serialize__(
            self: T,
            d: dict[Any, Any],
            # context: Any = None,  # added with ADD_SERIALIZATION_CONTEXT option
    ) -> dict[Any, Any]:
        return {k: v for k, v in d.items() if v}


@dataclass
class GuardFile(DataClassYAMLMixin):
    ammo_gt: int | None = None
    ammo_gte: int | None = None
    ammo_eq: int | None = None
    ammo_lt: int | None = None
    ammo_lte: int | None = None
    trigger_pressed: bool | None = None
    all: list["GuardFile"] = field(default_factory=list)
    any: list["GuardFile"] = field(default_factory=list)


@dataclass
class StateFile(DataClassYAMLMixin):
    id: str
    label: str
    on_entry: list[ActionFile] = field(default_factory=list)
    on_exit: list[ActionFile] = field(default_factory=list)


@dataclass
class TransitionFile(DataClassYAMLMixin):
    id: str
    source: str
    target: str
    trigger: str
    actions: list[ActionFile] = field(default_factory=list)
    guard: GuardFile | None = None


@dataclass
class GunFile(DataClassYAMLMixin):
    events: list[EventFile] = field(default_factory=list)


@dataclass
class WeaponFile(DataClassYAMLMixin):
    initial_state: str = "ready"
    variables: dict[str, Any] = field(default_factory=dict)
    states: list[StateFile] = field(default_factory=list)
    transitions: list[TransitionFile] = field(default_factory=list)


@dataclass
class WeaponProfileFile(DataClassYAMLMixin):
    weapon: WeaponFile = field(default_factory=WeaponFile)
    clips: dict[str, str] = field(default_factory=dict)
    clip_sets: dict[str, ClipSetFile] = field(default_factory=dict)
    light_sequences: dict[str, LightSequenceFile] = field(default_factory=dict)

    def __post_serialize__(
            self: T,
            d: dict[Any, Any],
            # context: Any = None,  # added with ADD_SERIALIZATION_CONTEXT option
    ) -> dict[Any, Any]:
        return {
            k: self.__post_serialize__(v) if isinstance(v, dict)
            else [self.__post_serialize__(vl) for vl in v] if isinstance(v, list)
            else v for k, v in d.items() if v
        }
