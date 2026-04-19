from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .actions import ActionDef
from .assets import ClipDef, LightSequenceDef


@dataclass(frozen=True)
class StateDef:
    id: str
    label: str | None = None
    on_entry: list[ActionDef] = field(default_factory=list)
    on_exit: list[ActionDef] = field(default_factory=list)


@dataclass(frozen=True)
class TransitionDef:
    id: str
    source: str
    trigger: str
    target: str
    guard: dict[str, Any] | None = None
    actions: list[ActionDef] = field(default_factory=list)


@dataclass(frozen=True)
class WeaponDef:
    initial_state: str
    variables: dict[str, Any] = field(default_factory=dict)
    clips: dict[str, ClipDef] = field(default_factory=dict)
    light_sequences: dict[str, LightSequenceDef] = field(default_factory=dict)
    states: list[StateDef] = field(default_factory=list)
    transitions: list[TransitionDef] = field(default_factory=list)
