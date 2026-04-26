from dataclasses import dataclass
import random

from weapon_fsm_core.domain.command_schema import CommandFieldSpec, ValidationContext
from weapon_fsm_core.domain.commands import GunRuntimeCommand, RuntimeCommand, RuntimeEnvironment


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
    clip_set: str
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
        clips = kwargs.get("clip_set")
        if not clips:
            raise ValueError("play_random_audio requires at least one clip")
        if context is not None:
            missing = [str(item) for item in clips if str(item) not in context.clips]
            if missing:
                quoted = ", ".join(repr(item) for item in missing)
                raise ValueError(f"Unknown clip(s): {quoted}")

    def execute(self, env: RuntimeEnvironment) -> None:
        clips = env.weapon.clip_sets[self.clip_set].clips

        if not clips:
            return
        PlayAudioCommand(
            clip=random.choice(clips),
            mode="one_shot",
            interrupt=self.interrupt,
        ).execute(env)


@dataclass(frozen=True, slots=True)
class PlayAudioEffectCommand(RuntimeCommand, action_type="play_audio_effect"):
    effect: str

    @classmethod
    def schema(cls) -> tuple[CommandFieldSpec, ...]:
        return (
            CommandFieldSpec("effect", required=True, expected_types=(str,), reference_target="audio_effects"),
        )

    def execute(self, env: RuntimeEnvironment) -> None:
        effect = env.weapon.audio_effects.get(self.effect)
        if effect is None or not effect.clips:
            return

        selected_clip = effect.clips[0]
        if effect.resolved_mode == "random":
            selected_clip = random.choice(effect.clips)

        resolved_mode = effect.resolved_mode
        if resolved_mode == "random":
            resolved_mode = "one_shot"

        PlayAudioCommand(
            clip=selected_clip,
            mode=resolved_mode,
            interrupt=effect.interrupt,
        ).execute(env)


@dataclass(frozen=True, slots=True)
class StopAudioCommand(RuntimeCommand, action_type="stop_audio"):
    def execute(self, env: RuntimeEnvironment) -> None:
        env.gun_commands.append(GunRuntimeCommand(type="stop_audio", payload={}))
