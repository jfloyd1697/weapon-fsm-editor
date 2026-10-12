from weapon_fsm_core.domain.model import ActionDef


class ActionFactory:
    @staticmethod
    def create(action_type: str, **arguments: object) -> ActionDef:
        return ActionDef(type=action_type, arguments=dict(arguments))

    @staticmethod
    def play_audio(clip: str, interrupt: str = "interrupt") -> ActionDef:
        return ActionDef(type="play_audio", arguments={"clip": clip, "interrupt": interrupt})

    @staticmethod
    def play_audio_loop(clip: str, interrupt: str = "interrupt") -> ActionDef:
        return ActionDef(type="play_audio_loop", arguments={"clip": clip, "interrupt": interrupt})

    @staticmethod
    def play_audio_effect(effect: str) -> ActionDef:
        return ActionDef(type="play_audio_effect", arguments={"effect": effect})

    @staticmethod
    def stop_audio() -> ActionDef:
        return ActionDef(type="stop_audio", arguments={})

    @staticmethod
    def schedule_event(event: str, delay_ms: int) -> ActionDef:
        return ActionDef(type="schedule_event", arguments={"event": event, "delay_ms": delay_ms})

    @staticmethod
    def set_var(name: str, value: object) -> ActionDef:
        return ActionDef(type="set_var", arguments={"name": name, "value": value})

    @staticmethod
    def add_var(name: str, value: object) -> ActionDef:
        return ActionDef(type="add_var", arguments={"name": name, "value": value})

    @staticmethod
    def start_light_sequence(sequence: str) -> ActionDef:
        return ActionDef(type="start_light_sequence", arguments={"sequence": sequence})
