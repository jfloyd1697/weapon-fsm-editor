import enum
import random
import typing
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from typing import ClassVar

from .command_schema import CommandFieldSpec, ValidationContext
from .model import ActionDef, WeaponConfig
from .runtime_types import ScheduledEvent


@dataclass
class RuntimeEnvironment:
    weapon: WeaponConfig
    variables: dict[str, object]
    clip_set_state: dict[str, dict[str, int | str | tuple[int, ...]]]
    emitted_events: list[str] = field(default_factory=list)
    scheduled_events: list[ScheduledEvent] = field(default_factory=list)
    gun_commands: list["GunRuntimeCommand"] = field(default_factory=list)


@dataclass(frozen=True)
class RuntimeCommand:
    _registry: ClassVar[dict[str, type["RuntimeCommand"]]] = {}

    def __init_subclass__(cls, *, action_type: str | None = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if action_type is not None:
            RuntimeCommand._registry[action_type] = cls

    def execute(self, env: RuntimeEnvironment) -> None:
        raise NotImplementedError

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return ()

    @classmethod
    def from_action(cls, action: ActionDef) -> "RuntimeCommand":
        command_type = cls._registry.get(action.type)
        if command_type is None:
            return GunRuntimeCommand(type=action.type, payload=dict(action.arguments))

        kwargs = cls._build_kwargs(action, command_type)
        command_type.validate_kwargs(kwargs, None)
        return command_type(**kwargs)

    @classmethod
    def validate_action(
        cls,
        action: ActionDef,
        context: ValidationContext | None = None,
    ) -> list[str]:
        command_type = cls._registry.get(action.type)
        if command_type is None:
            return []

        try:
            kwargs = cls._build_kwargs(action, command_type)
        except Exception as exc:
            return [str(exc)]

        errors: list[str] = []
        for field_spec in command_type.schema():
            if field_spec.name in kwargs:
                errors.extend(field_spec.validate(kwargs[field_spec.name], context))

        try:
            command_type.validate_kwargs(kwargs, context)
        except Exception as exc:
            errors.append(str(exc))

        return errors

    @staticmethod
    def _build_kwargs(
        action: ActionDef,
        command_type: type["RuntimeCommand"],
    ) -> dict[str, object]:
        if not is_dataclass(command_type):
            raise TypeError(f"{command_type.__name__} must be a dataclass")

        kwargs: dict[str, object] = {}
        for field_info in fields(command_type):
            if not field_info.init:
                continue

            if field_info.name in action.arguments:
                value = action.arguments[field_info.name]
                if field_info.name == "clips" and isinstance(value, list):
                    value = tuple(str(item) for item in value)
                kwargs[field_info.name] = value
                continue

            has_default = field_info.default is not MISSING
            has_default_factory = field_info.default_factory is not MISSING
            if has_default or has_default_factory:
                continue

            raise ValueError(
                f"Action '{action.type}' is missing required argument '{field_info.name}'"
            )

        return kwargs

    @classmethod
    def validate_kwargs(
        cls,
        kwargs: dict[str, object],
        context: ValidationContext | None = None,
    ) -> None:
        return


class GunCommandType(enum.StrEnum):
    PLAY_AUDIO = "play_audio"
    STOP_AUDIO = "stop_audio"
    PLAY_LIGHT = "play_light"
    STOP_LIGHT = "stop_light"


@dataclass(frozen=True)
class GunRuntimeCommand(RuntimeCommand):
    type: str
    payload: dict[str, object] = field(default_factory=dict)

    def execute(self, env: RuntimeEnvironment) -> None:
        env.gun_commands.append(self)

    @classmethod
    def play_audio(cls, payload: dict[str, object]) -> typing.Self:
        return cls(type=GunCommandType.PLAY_AUDIO, payload=payload)

    @classmethod
    def stop_audio(cls, payload: dict[str, object]) -> typing.Self:
        return cls(type=GunCommandType.STOP_AUDIO, payload=payload)

    @classmethod
    def play_light(cls, payload: dict[str, object]) -> typing.Self:
        return cls(type=GunCommandType.PLAY_LIGHT, payload=payload)

    @classmethod
    def stop_light(cls) -> typing.Self:
        return cls(type=GunCommandType.STOP_LIGHT, payload={})



@dataclass(frozen=True, slots=True)
class PlayLightCommand(RuntimeCommand, action_type=GunCommandType.PLAY_LIGHT):
    sequence: str
    mode: str = "one_shot"

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("sequence", required=True, expected_types=(str,), reference_target="light_sequences"),
            CommandFieldSpec(
                "mode",
                expected_types=(str,),
                enum_values=("one_shot", "loop"),
            ),
        )

    def execute(self, env: RuntimeEnvironment) -> None:
        sequence_def = env.weapon.light_sequences.get(self.sequence)
        path = env.weapon.resolve_asset_path(sequence_def.path) if sequence_def is not None else self.sequence
        env.gun_commands.append(
            GunRuntimeCommand.play_light(
                payload={
                    "sequence": self.sequence,
                    "path": path,
                    "mode": self.mode,
                },
            )
        )


@dataclass(frozen=True, slots=True)
class StopLightCommand(RuntimeCommand, action_type="stop_light"):
    def execute(self, env: RuntimeEnvironment) -> None:
        env.gun_commands.append(GunRuntimeCommand.stop_light())


@dataclass(frozen=True, slots=True)
class StartLightSequenceCommand(RuntimeCommand, action_type="start_light_sequence"):
    sequence: str

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (CommandFieldSpec("sequence", required=True, expected_types=(str,), reference_target="light_sequences"),)

    def execute(self, env: RuntimeEnvironment) -> None:
        PlayLightCommand(sequence=self.sequence, mode="loop").execute(env)


@dataclass(frozen=True, slots=True)
class StopLightSequenceCommand(RuntimeCommand, action_type="stop_light_sequence"):
    def execute(self, env: RuntimeEnvironment) -> None:
        StopLightCommand().execute(env)


@dataclass(frozen=True, slots=True)
class SetVarCommand(RuntimeCommand, action_type="set_var"):
    name: str
    value: object | None = None
    value_from_var: str | None = None

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("name", required=True, expected_types=(str,), reference_target="variables"),
            CommandFieldSpec("value_from_var", expected_types=(str,), reference_target="variables"),
        )

    @classmethod
    def validate_kwargs(
        cls,
        kwargs: dict[str, object],
        context: ValidationContext | None = None,
    ) -> None:
        has_value = "value" in kwargs and kwargs["value"] is not None
        has_value_from_var = "value_from_var" in kwargs and kwargs["value_from_var"] is not None
        if has_value and has_value_from_var:
            raise ValueError("set_var cannot specify both 'value' and 'value_from_var'")
        if not has_value and not has_value_from_var:
            raise ValueError("set_var requires either 'value' or 'value_from_var'")

    def execute(self, env: RuntimeEnvironment) -> None:
        if self.value_from_var is not None:
            env.variables[self.name] = env.variables.get(self.value_from_var)
        else:
            env.variables[self.name] = self.value


@dataclass(frozen=True, slots=True)
class AddVarCommand(RuntimeCommand, action_type="add_var"):
    name: str
    value: object = 0

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (CommandFieldSpec("name", required=True, expected_types=(str,), reference_target="variables"),)

    def execute(self, env: RuntimeEnvironment) -> None:
        current = env.variables.get(self.name, 0)
        env.variables[self.name] = current + self.value


@dataclass(frozen=True, slots=True)
class AdjustAmmoCommand(RuntimeCommand, action_type="adjust_ammo"):
    delta: int = 0

    def execute(self, env: RuntimeEnvironment) -> None:
        ammo = int(env.variables.get("ammo", 0))
        mag_capacity = int(env.variables.get("mag_capacity", ammo))
        env.variables["ammo"] = max(0, min(mag_capacity, ammo + self.delta))


@dataclass(frozen=True, slots=True)
class SetAmmoCommand(RuntimeCommand, action_type="set_ammo"):
    value: int = 0

    def execute(self, env: RuntimeEnvironment) -> None:
        mag_capacity = int(env.variables.get("mag_capacity", self.value))
        env.variables["ammo"] = max(0, min(mag_capacity, self.value))


@dataclass(frozen=True, slots=True)
class SetAmmoFullCommand(RuntimeCommand, action_type="set_ammo_full"):
    def execute(self, env: RuntimeEnvironment) -> None:
        env.variables["ammo"] = int(env.variables.get("mag_capacity", 0))


@dataclass(frozen=True, slots=True)
class EmitEventCommand(RuntimeCommand, action_type="emit_event"):
    event: str

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (CommandFieldSpec("event", required=True, expected_types=(str,), reference_target="events"),)

    def execute(self, env: RuntimeEnvironment) -> None:
        env.emitted_events.append(self.event)


@dataclass(frozen=True, slots=True)
class ScheduleEventCommand(RuntimeCommand, action_type="schedule_event"):
    event: str
    delay_ms: int = 0

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("event", required=True, expected_types=(str,), reference_target="events"),
            CommandFieldSpec("delay_ms", expected_types=(int,)),
        )

    def execute(self, env: RuntimeEnvironment) -> None:
        env.scheduled_events.append(ScheduledEvent(self.event, self.delay_ms))


@dataclass(frozen=True, slots=True)
class ChanceEventCommand(RuntimeCommand, action_type="chance_event"):
    event: str
    chance: float = 0.0

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("event", required=True, expected_types=(str,), reference_target="events"),
            CommandFieldSpec("chance", expected_types=(int, float)),
        )

    @classmethod
    def validate_kwargs(
        cls,
        kwargs: dict[str, object],
        context: ValidationContext | None = None,
    ) -> None:
        chance = float(kwargs.get("chance", 0.0))
        if chance < 0.0 or chance > 1.0:
            raise ValueError("chance_event 'chance' must be between 0.0 and 1.0")

    def execute(self, env: RuntimeEnvironment) -> None:
        if random.random() <= self.chance:
            env.emitted_events.append(self.event)


@dataclass(frozen=True, slots=True)
class LogCommand(RuntimeCommand, action_type="log"):
    message: str = ""

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (CommandFieldSpec("message", expected_types=(str,)),)

    def execute(self, env: RuntimeEnvironment) -> None:
        env.gun_commands.append(
            GunRuntimeCommand(type="log", payload={"message": self.message})
        )
