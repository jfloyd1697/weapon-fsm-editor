from dataclasses import dataclass, field
from typing import Any

from .mixins import DataClassYAMLMixin


@dataclass
class EventFile(DataClassYAMLMixin):
    id: str
    label: str | None = None
    kind: str = "external"


@dataclass
class ActionFile(DataClassYAMLMixin):
    type: str
    arguments: dict[str, Any] = field(default_factory=dict)
    sound: str | None = None
    clip: str | None = None
    clips: list[str] = field(default_factory=list)
    pattern: str | None = None
    sequence: str | None = None
    event: str | None = None
    delay_ms: int | None = None
    delta: int | None = None
    value: int | None = None
    interrupt: str | None = None


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
    mag_capacity: int = 30
    initial_ammo: int | None = None
    initial_state: str = "ready"
    states: list[StateFile] = field(default_factory=list)
    transitions: list[TransitionFile] = field(default_factory=list)
