from dataclasses import dataclass
import random

from weapon_fsm_core.domain.command_schema import CommandFieldSpec, ValidationContext
from weapon_fsm_core.domain.commands import GunRuntimeCommand, RuntimeCommand, RuntimeEnvironment, GunCommandType


@dataclass(frozen=True, slots=True)
class PlayAudioCommand(RuntimeCommand, action_type=GunCommandType.PLAY_AUDIO):
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
            GunRuntimeCommand.play_audio(
                payload={
                    "clip": self.clip,
                    "path": path,
                    "mode": self.mode,
                    "interrupt": self.interrupt,
                },
            )
        )


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


# @dataclass(frozen=True, slots=True)
# class PlayRandomAudioCommand(RuntimeCommand, action_type="play_audio_random"):
#     clips: tuple[str, ...]
#     clip_set: str
#     interrupt: str = "interrupt"
#
#     @classmethod
#     def schema(cls) -> tuple[CommandFieldSpec, ...]:
#         return (
#             CommandFieldSpec("clips", required=True, expected_types=(tuple,)),
#             CommandFieldSpec(
#                 "interrupt",
#                 expected_types=(str,),
#                 enum_values=("interrupt", "schedule", "ignore"),
#             ),
#         )
#
#     @classmethod
#     def validate_kwargs(
#         cls,
#         kwargs: dict[str, object],
#         context: ValidationContext | None = None,
#     ) -> None:
#         clips = kwargs.get("clips", ())
#         if not clips:
#             raise ValueError("play_random_audio requires at least one clip")
#         if context is not None:
#             missing = [str(item) for item in clips if str(item) not in context.clips]
#             if missing:
#                 quoted = ", ".join(repr(item) for item in missing)
#                 raise ValueError(f"Unknown clip(s): {quoted}")
#
#     def execute(self, env: RuntimeEnvironment) -> None:
#         if not self.clips:
#             return
#
#
#
#         PlayAudioCommand(
#             clip=random.choice(self.clips),
#             mode="one_shot",
#             interrupt=self.interrupt,
#         ).execute(env)


@dataclass(frozen=True, slots=True)
class PlayAudioRandomCommand(RuntimeCommand, action_type="play_audio_random"):
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
        selected_clip = _choose_clip_from_set(env, self.clip_set)
        if selected_clip is None:
            return
        PlayAudioCommand(
            clip=selected_clip,
            mode="one_shot",
            interrupt=self.interrupt,
        ).execute(env)


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
