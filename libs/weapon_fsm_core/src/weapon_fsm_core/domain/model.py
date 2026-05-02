from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from mashumaro import DataClassDictMixin

from .enums import AudioInterrupt, AudioMode, ClipSetMode


@dataclass(frozen=True)
class ActionDef(DataClassDictMixin):
    type: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def __pre_deserialize__(cls, value: dict[str, Any]) -> dict[str, Any]:
        if "arguments" in value and isinstance(value["arguments"], dict):
            return value

        return {
            "type": value["type"],
            "arguments": {
                key: item
                for key, item in value.items()
                if key != "type"
            },
        }

    def argument(self, name: str, default: Any = None) -> Any:
        return self.arguments.get(name, default)


@dataclass(frozen=True)
class GuardDef(DataClassDictMixin):
    all: list["GuardDef"] = field(default_factory=list)
    any: list["GuardDef"] = field(default_factory=list)

    trigger_pressed: bool | None = None

    var_eq: dict[str, Any] | None = None
    var_gt: dict[str, Any] | None = None
    var_gte: dict[str, Any] | None = None
    var_lt: dict[str, Any] | None = None
    var_lte: dict[str, Any] | None = None

    def evaluate(
        self,
        *,
        variables: dict[str, object],
        trigger_pressed: bool,
    ) -> bool:
        if self.all and not all(
            guard.evaluate(
                variables=variables,
                trigger_pressed=trigger_pressed,
            )
            for guard in self.all
        ):
            return False

        if self.any and not any(
            guard.evaluate(
                variables=variables,
                trigger_pressed=trigger_pressed,
            )
            for guard in self.any
        ):
            return False

        if self.trigger_pressed is not None:
            if trigger_pressed != self.trigger_pressed:
                return False

        return (
            self._compare(self.var_eq, variables, lambda left, right: left == right)
            and self._compare(self.var_gt, variables, lambda left, right: left > right)
            and self._compare(self.var_gte, variables, lambda left, right: left >= right)
            and self._compare(self.var_lt, variables, lambda left, right: left < right)
            and self._compare(self.var_lte, variables, lambda left, right: left <= right)
        )

    def _compare(
        self,
        spec: dict[str, Any] | None,
        variables: dict[str, object],
        compare,
    ) -> bool:
        if spec is None:
            return True

        left = variables.get(str(spec["name"]))

        if "value_from_var" in spec:
            right = variables.get(str(spec["value_from_var"]))
        else:
            right = spec.get("value")

        return compare(left, right)


@dataclass(frozen=True)
class ClipDef(DataClassDictMixin):
    name: str
    path: str
    preload: bool = True


@dataclass(frozen=True)
class ClipSetDef(DataClassDictMixin):
    name: str
    clips: list[str] = field(default_factory=list)
    mode: ClipSetMode = ClipSetMode.RANDOM


@dataclass(frozen=True)
class AudioEffectDef(DataClassDictMixin):
    name: str
    clips: list[str] = field(default_factory=list)
    mode: AudioMode = AudioMode.ONCE
    interrupt: AudioInterrupt = AudioInterrupt.INTERRUPT
    loop: bool = False
    gain: float = 1.0


@dataclass(frozen=True)
class LightSequenceDef(DataClassDictMixin):
    name: str
    path: str
    preload: bool = True


@dataclass(frozen=True)
class StateDef(DataClassDictMixin):
    id: str
    label: str = ""
    on_entry: list[ActionDef] = field(default_factory=list)
    on_exit: list[ActionDef] = field(default_factory=list)


@dataclass(frozen=True)
class TransitionDef(DataClassDictMixin):
    id: str
    source: str
    trigger: str
    target: str
    guard: GuardDef | None = None
    actions: list[ActionDef] = field(default_factory=list)
    internal: bool = False


@dataclass(frozen=True)
class GunConfig(DataClassDictMixin):
    events: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WeaponConfig(DataClassDictMixin):
    initial_state: str = "ready"
    variables: dict[str, Any] = field(default_factory=dict)

    states: dict[str, StateDef] = field(default_factory=dict)
    transitions: list[TransitionDef] = field(default_factory=list)

    clips: dict[str, ClipDef] = field(default_factory=dict)
    clip_sets: dict[str, ClipSetDef] = field(default_factory=dict)
    audio_effects: dict[str, AudioEffectDef] = field(default_factory=dict)
    light_sequences: dict[str, LightSequenceDef] = field(default_factory=dict)

    source_path: Path | None = None

    def transitions_from(self, state_id: str) -> list[TransitionDef]:
        return [transition for transition in self.transitions if transition.source == state_id]

    def resolve_asset_path(self, path: str) -> Path:
        candidate = Path(path)

        if candidate.is_absolute() or self.source_path is None:
            return candidate

        return self.source_path / candidate
