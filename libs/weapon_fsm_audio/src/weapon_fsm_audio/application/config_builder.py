from weapon_fsm_core.application.builders import WeaponProfileBuilder
from weapon_fsm_core import ActionFactory


class AudioConfigBuilder:
    def __init__(self, profile_builder: WeaponProfileBuilder | None = None):
        self._profile_builder = profile_builder or WeaponProfileBuilder()

    @property
    def profile_builder(self) -> WeaponProfileBuilder:
        return self._profile_builder

    def set_clip(self, name: str, path: str, preload: bool = True) -> "AudioConfigBuilder":
        self._profile_builder.set_clip(name, path, preload=preload)
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
            self._profile_builder.remove_transition_actions_by_type(
                transition_id,
                "play_audio_effect",
            )
        self._profile_builder.append_transition_action(
            transition_id,
            ActionFactory.play_audio_effect(effect),
        )
        return self

    def bind_state_entry_effect(
        self,
        state_id: str,
        effect: str,
        replace_existing: bool = False,
    ) -> "AudioConfigBuilder":
        if replace_existing:
            self._profile_builder.remove_state_entry_actions_by_type(
                state_id,
                "play_audio_effect",
            )
        self._profile_builder.append_state_entry_action(
            state_id,
            ActionFactory.play_audio_effect(effect),
        )
        return self

    def bind_state_exit_effect(
        self,
        state_id: str,
        effect: str,
        replace_existing: bool = False,
    ) -> "AudioConfigBuilder":
        if replace_existing:
            self._profile_builder.remove_state_exit_actions_by_type(
                state_id,
                "play_audio_effect",
            )
        self._profile_builder.append_state_exit_action(
            state_id,
            ActionFactory.play_audio_effect(effect),
        )
        return self

    def add_stop_audio_to_transition(self, transition_id: str) -> "AudioConfigBuilder":
        self._profile_builder.append_transition_action(
            transition_id,
            ActionFactory.stop_audio(),
        )
        return self