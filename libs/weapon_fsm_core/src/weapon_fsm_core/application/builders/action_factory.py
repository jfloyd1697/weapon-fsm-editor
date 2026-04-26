from dataclasses import dataclass, field

from weapon_fsm_core.domain.model import ActionDef


@dataclass
class ActionConfig:
    type: str
    clip: str | None = None
    effect: str | None = None
    event: str | None = None
    delay_ms: int | None = None
    variable: str | None = None
    value: int | float | bool | str | None = None
    sequence: str | None = None
    loop: bool | None = None
    interrupt: str | None = None
    gain: float | None = None
    params: dict[str, object] = field(default_factory=dict)

    def action_def(self):
        data = self.__dict__.copy()
        data.update(self.params)
        return ActionDef(
            type=self.type,
            arguments=data,
        )


class ActionFactory:
    @staticmethod
    def play_audio(clip: str, *, gain: float | None = None) -> ActionDef:
        return ActionConfig(type="play_audio", clip=clip, gain=gain).action_def()

    @staticmethod
    def play_audio_loop(clip: str, *, gain: float | None = None) -> ActionDef:
        return ActionConfig(type="play_audio_loop", clip=clip, gain=gain, loop=True).action_def()

    @staticmethod
    def play_audio_effect(effect: str) -> ActionDef:
        return ActionConfig(type="play_audio_effect", effect=effect).action_def()

    @staticmethod
    def play_random_audio(clips: list[str] | tuple[str, ...]) -> ActionDef:
        return ActionConfig(type="play_random_audio", params={"clips": list(clips)}).action_def()

    @staticmethod
    def stop_audio() -> ActionDef:
        return ActionConfig(type="stop_audio").action_def()

    @staticmethod
    def schedule_event(event: str, delay_ms: int) -> ActionDef:
        return ActionConfig(type="schedule_event", event=event, delay_ms=delay_ms).action_def()

    @staticmethod
    def cancel_scheduled_event(event: str) -> ActionDef:
        return ActionConfig(type="cancel_scheduled_event", event=event).action_def()

    @staticmethod
    def set_variable(name: str, value: int | float | bool | str) -> ActionDef:
        return ActionConfig(type="set_variable", variable=name, value=value).action_def()

    @staticmethod
    def increment_variable(name: str, amount: int = 1) -> ActionDef:
        return ActionConfig(type="increment_variable", variable=name, value=amount).action_def()

    @staticmethod
    def decrement_variable(name: str, amount: int = 1) -> ActionDef:
        return ActionConfig(type="decrement_variable", variable=name, value=amount).action_def()

    @staticmethod
    def start_light_sequence(sequence: str) -> ActionDef:
        return ActionConfig(type="start_light_sequence", sequence=sequence).action_def()

    @staticmethod
    def stop_light_sequence(sequence: str | None = None) -> ActionDef:
        action = ActionConfig(type="stop_light_sequence")
        if sequence is not None:
            action.sequence = sequence
        return action.action_def()
