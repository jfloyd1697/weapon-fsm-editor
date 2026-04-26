from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Type, Mapping, Dict

from mashumaro import DataClassDictMixin
from mashumaro.mixins.dict import T


@dataclass(frozen=True)
class ActionDef(DataClassDictMixin):
    type: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def __pre_deserialize__(cls, d: Dict[Any, Any]) -> Dict[Any, Any]:
        raw = dict(d)
        data = {}
        if d.get("type"):
            data["type"] = raw.pop("type")
        data["arguments"] = raw
        return data

    def argument(self, name: str, default: object = None) -> object:
        return self.arguments.get(name, default)


@dataclass(frozen=True)
class ClipDef(DataClassDictMixin):
    name: str
    path: str
    preload: bool = True


@dataclass(frozen=True)
class LightSequenceDef(DataClassDictMixin):
    name: str
    path: str
    preload: bool = True


@dataclass(frozen=True)
class ClipSetDef(DataClassDictMixin):
    name: str
    clips: tuple[str, ...]
    mode: str = "random"


@dataclass(frozen=True)
class GuardDef(DataClassDictMixin):
    all: tuple["GuardDef", ...] = ()
    any: tuple["GuardDef", ...] = ()
    trigger_pressed: bool | None = None

    var_eq: dict[str, Any] | None = None
    var_gt: dict[str, Any] | None = None
    var_gte: dict[str, Any] | None = None
    var_lt: dict[str, Any] | None = None
    var_lte: dict[str, Any] | None = None

    def evaluate(
        self,
        variables: dict[str, object],
        trigger_pressed: bool,
    ) -> bool:
        if self.trigger_pressed is not None and self.trigger_pressed != trigger_pressed:
            return False

        if self.var_eq is not None and not self._compare(variables, self.var_eq, "eq"):
            return False
        if self.var_gt is not None and not self._compare(variables, self.var_gt, "gt"):
            return False
        if self.var_gte is not None and not self._compare(variables, self.var_gte, "gte"):
            return False
        if self.var_lt is not None and not self._compare(variables, self.var_lt, "lt"):
            return False
        if self.var_lte is not None and not self._compare(variables, self.var_lte, "lte"):
            return False

        if self.all and not all(item.evaluate(variables, trigger_pressed) for item in self.all):
            return False

        if self.any and not any(item.evaluate(variables, trigger_pressed) for item in self.any):
            return False

        return True

    def _compare(
        self,
        variables: dict[str, object],
        spec: dict[str, object],
        op: str,
    ) -> bool:
        name = str(spec["name"])
        left = variables.get(name)

        if "value_from_var" in spec:
            right = variables.get(str(spec["value_from_var"]))
        else:
            right = spec.get("value")

        if op == "eq":
            return left == right
        if op == "gt":
            return left > right
        if op == "gte":
            return left >= right
        if op == "lt":
            return left < right
        if op == "lte":
            return left <= right

        raise ValueError(f"Unsupported guard op: {op}")


@dataclass(frozen=True)
class StateDef(DataClassDictMixin):
    id: str
    label: str
    on_entry: tuple[ActionDef, ...] = ()
    on_exit: tuple[ActionDef, ...] = ()


@dataclass(frozen=True)
class TransitionDef(DataClassDictMixin):
    id: str
    source: str
    trigger: str
    target: str
    guard: GuardDef | None = None
    actions: tuple[ActionDef, ...] = ()


@dataclass(frozen=True)
class GunConfig(DataClassDictMixin):
    events: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeaponConfig(DataClassDictMixin):
    initial_state: str
    states: tuple[StateDef, ...]
    transitions: tuple[TransitionDef, ...]
    variables: dict[str, Any] = field(default_factory=dict)
    clips: dict[str, ClipDef] = field(default_factory=dict)
    clip_sets: dict[str, ClipSetDef] = field(default_factory=dict)
    light_sequences: dict[str, LightSequenceDef] = field(default_factory=dict)
    source_path: Path | None = None

    def transitions_from(self, state_id: str) -> tuple[TransitionDef, ...]:
        return tuple(
            transition for transition in self.transitions if transition.source == state_id
        )

    def resolve_asset_path(self, relative_path: str) -> str:
        if self.source_path is None:
            return relative_path
        return str((self.source_path.parent / relative_path).resolve())

    def get_state(self, current_state):
        for state in self.states:
            if state.id == current_state:
                return state
        raise ValueError(f"Unsupported state id: {current_state}")
