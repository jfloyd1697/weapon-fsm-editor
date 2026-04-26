from pathlib import Path

from weapon_fsm_core.infrastructure.yaml.profile_builder import ActionBuilder, WeaponProfileBuilder


class AudioConfigBuilder:
    def __init__(self, profile_builder: WeaponProfileBuilder | None = None):
        self._profile_builder = profile_builder or WeaponProfileBuilder()

    @classmethod
    def from_yaml(cls, text: str) -> "AudioConfigBuilder":
        return cls(WeaponProfileBuilder.from_yaml(text))

    @classmethod
    def from_file(cls, path: str | Path) -> "AudioConfigBuilder":
        return cls(WeaponProfileBuilder.from_file(path))

    @property
    def profile_builder(self) -> WeaponProfileBuilder:
        return self._profile_builder

    def set_clip(self, name: str, path: str, preload: bool = True) -> "AudioConfigBuilder":
        self._profile_builder.set_audio_clip(name, path, preload=preload)
        return self

    def set_effect(
        self,
        name: str,
        *,
        clips: list[str] | tuple[str, ...] | None = None,
        clip: str | None = None,
        mode: str = "one_shot",
        interrupt: str = "interrupt",
        loop: bool = False,
        gain: float = 1.0,
    ) -> "AudioConfigBuilder":
        self._profile_builder.set_audio_effect(
            name,
            clips=clips,
            clip=clip,
            mode=mode,
            interrupt=interrupt,
            loop=loop,
            gain=gain,
        )
        return self

    def bind_transition_effect(
        self,
        transition_id: str,
        effect: str,
        replace_existing: bool = False,
    ) -> "AudioConfigBuilder":
        if replace_existing:
            transition = self._profile_builder._require_transition(transition_id)
            transition.actions = [
                action for action in transition.actions if action.type != "play_audio_effect"
            ]
        self._profile_builder.append_transition_action(
            transition_id,
            ActionBuilder.play_audio_effect(effect),
        )
        return self

    def bind_state_entry_effect(
        self,
        state_id: str,
        effect: str,
        replace_existing: bool = False,
    ) -> "AudioConfigBuilder":
        state = self._profile_builder.ensure_state(state_id)
        if replace_existing:
            state.on_entry = [action for action in state.on_entry if action.type != "play_audio_effect"]
        self._profile_builder.append_state_entry_action(
            state_id,
            ActionBuilder.play_audio_effect(effect),
        )
        return self

    def bind_state_exit_effect(
        self,
        state_id: str,
        effect: str,
        replace_existing: bool = False,
    ) -> "AudioConfigBuilder":
        state = self._profile_builder.ensure_state(state_id)
        if replace_existing:
            state.on_exit = [action for action in state.on_exit if action.type != "play_audio_effect"]
        self._profile_builder.append_state_exit_action(
            state_id,
            ActionBuilder.play_audio_effect(effect),
        )
        return self

    def add_stop_audio_to_transition(self, transition_id: str) -> "AudioConfigBuilder":
        self._profile_builder.append_transition_action(transition_id, ActionBuilder.stop_audio())
        return self

    def to_yaml(self) -> str:
        return self._profile_builder.to_yaml()

    def write(self, path: str | Path) -> Path:
        return self._profile_builder.write(path)
