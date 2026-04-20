from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields, is_dataclass
import random
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


@dataclass(frozen=True)
class GunRuntimeCommand(RuntimeCommand):
    type: str
    payload: dict[str, object] = field(default_factory=dict)

    def execute(self, env: RuntimeEnvironment) -> None:
        env.gun_commands.append(self)


@dataclass(frozen=True, slots=True)
class PlayAudioCommand(RuntimeCommand, action_type="play_audio"):
    clip: str
    mode: str = "one_shot"
    interrupt: str = "interrupt"

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("clip", required=True, expected_types=(str,), reference_target="clips"),
            CommandFieldSpec(
                "mode",
                expected_types=(str,),
                enum_values=("one_shot", "loop"),
            ),
            CommandFieldSpec(
                "interrupt",
                expected_types=(str,),
                enum_values=("interrupt", "schedule", "ignore"),
            ),
        )

    def execute(self, env: RuntimeEnvironment) -> None:
        clip_def = env.weapon.clips.get(self.clip)
        path = env.weapon.resolve_asset_path(clip_def.path) if clip_def is not None else self.clip
        env.gun_commands.append(
            GunRuntimeCommand(
                type="play_audio",
                payload={
                    "clip": self.clip,
                    "path": path,
                    "mode": self.mode,
                    "interrupt": self.interrupt,
                },
            )
        )


@dataclass(frozen=True, slots=True)
class PlaySoundCommand(PlayAudioCommand, action_type="play_sound"):
    pass


@dataclass(frozen=True, slots=True)
class PlayAudioLoopCommand(RuntimeCommand, action_type="play_audio_loop"):
    clip: str
    interrupt: str = "interrupt"

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("clip", required=True, expected_types=(str,), reference_target="clips"),
            CommandFieldSpec(
                "interrupt",
                expected_types=(str,),
                enum_values=("interrupt", "schedule", "ignore"),
            ),
        )

    def execute(self, env: RuntimeEnvironment) -> None:
        PlayAudioCommand(clip=self.clip, mode="loop", interrupt=self.interrupt).execute(env)


@dataclass(frozen=True, slots=True)
class PlayRandomAudioCommand(RuntimeCommand, action_type="play_random_audio"):
    clips: tuple[str, ...]
    interrupt: str = "interrupt"

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("clips", required=True, expected_types=(tuple,)),
            CommandFieldSpec(
                "interrupt",
                expected_types=(str,),
                enum_values=("interrupt", "schedule", "ignore"),
            ),
        )

    @classmethod
    def validate_kwargs(
        cls,
        kwargs: dict[str, object],
        context: ValidationContext | None = None,
    ) -> None:
        clips = kwargs.get("clips", ())
        if not clips:
            raise ValueError("play_random_audio requires at least one clip")
        if context is not None:
            missing = [str(item) for item in clips if str(item) not in context.clips]
            if missing:
                quoted = ", ".join(repr(item) for item in missing)
                raise ValueError(f"Unknown clip(s): {quoted}")

    def execute(self, env: RuntimeEnvironment) -> None:
        if not self.clips:
            return
        PlayAudioCommand(
            clip=random.choice(self.clips),
            mode="one_shot",
            interrupt=self.interrupt,
        ).execute(env)


@dataclass(frozen=True, slots=True)
class PlaySoundRandomCommand(RuntimeCommand, action_type="play_sound_random"):
    clip_set: str
    interrupt: str = "interrupt"

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("clip_set", required=True, expected_types=(str,), reference_target="clip_sets"),
            CommandFieldSpec(
                "interrupt",
                expected_types=(str,),
                enum_values=("interrupt", "schedule", "ignore"),
            ),
        )

    def execute(self, env: RuntimeEnvironment) -> None:
        selected_clip = _choose_clip_from_set(env, self.clip_set)
        if selected_clip is None:
            return
        PlayAudioCommand(
            clip=selected_clip,
            mode="one_shot",
            interrupt=self.interrupt,
        ).execute(env)


@dataclass(frozen=True, slots=True)
class StopAudioCommand(RuntimeCommand, action_type="stop_audio"):
    def execute(self, env: RuntimeEnvironment) -> None:
        env.gun_commands.append(GunRuntimeCommand(type="stop_audio", payload={}))


@dataclass(frozen=True, slots=True)
class PlayLightCommand(RuntimeCommand, action_type="play_light"):
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
            GunRuntimeCommand(
                type="play_light",
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
        env.gun_commands.append(GunRuntimeCommand(type="stop_light", payload={}))


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
class SetAmmoFullCommand(RuntimeCommand, action_type="set_ammo_full"):
    def execute(self, env: RuntimeEnvironment) -> None:
        env.gun_commands.append(GunRuntimeCommand(type="set_ammo_full", payload={}))


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
    delay_ms: int

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("event", required=True, expected_types=(str,), reference_target="events"),
            CommandFieldSpec("delay_ms", required=True, expected_types=(int,)),
        )

    def execute(self, env: RuntimeEnvironment) -> None:
        env.scheduled_events.append(ScheduledEvent(event_id=self.event, delay_ms=self.delay_ms))


def _choose_clip_from_set(env: RuntimeEnvironment, clip_set_name: str) -> str | None:
    clip_set = env.weapon.clip_sets.get(clip_set_name)
    if clip_set is None or not clip_set.clips:
        return None

    state = env.clip_set_state.setdefault(clip_set_name, {})
    mode = clip_set.mode
    clips = clip_set.clips

    if mode == "sequence":
        index = int(state.get("index", 0))
        selected_index = index % len(clips)
        state["index"] = selected_index + 1
        return clips[selected_index]

    if mode == "random_no_repeat":
        last_index = state.get("last_index")
        choices = [idx for idx in range(len(clips)) if idx != last_index]
        if not choices:
            choices = [0]
        selected_index = random.choice(choices)
        state["last_index"] = selected_index
        return clips[selected_index]

    selected_index = random.randrange(len(clips))
    state["last_index"] = selected_index
    return clips[selected_index]
