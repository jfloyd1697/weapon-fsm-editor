from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActionDef:
    type: str
    arguments: dict[str, object] = field(default_factory=dict)

    def argument(self, name: str, default: object = None) -> object:
        return self.arguments.get(name, default)


@dataclass(frozen=True)
class GuardDef:
    all: tuple["GuardDef", ...] = ()
    any: tuple["GuardDef", ...] = ()
    trigger_pressed: bool | None = None

    var_eq: dict[str, object] | None = None
    var_gt: dict[str, object] | None = None
    var_gte: dict[str, object] | None = None
    var_lt: dict[str, object] | None = None
    var_lte: dict[str, object] | None = None

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
class StateDef:
    id: str
    label: str
    on_entry: tuple[ActionDef, ...] = ()
    on_exit: tuple[ActionDef, ...] = ()


@dataclass(frozen=True)
class TransitionDef:
    id: str
    source: str
    trigger: str
    target: str
    guard: GuardDef | None = None
    actions: tuple[ActionDef, ...] = ()


@dataclass(frozen=True)
class GunConfig:
    events: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeaponConfig:
    initial_state: str
    variables: dict[str, object]
    states: dict[str, StateDef]
    transitions: tuple[TransitionDef, ...]

    def transitions_from(self, state_id: str) -> tuple[TransitionDef, ...]:
        return tuple(
            transition for transition in self.transitions if transition.source == state_id
        )