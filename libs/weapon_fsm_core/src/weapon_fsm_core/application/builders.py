"""In-memory construction of weapon profiles without YAML-specific logic."""

from weapon_fsm_core.domain.model import (
    ActionDef,
    AudioEffectDef,
    ClipDef,
    GunConfig,
    StateDef,
    TransitionDef,
    WeaponConfig,
)


class ActionFactory:
    @staticmethod
    def create(action_type: str, **arguments: object) -> ActionDef:
        return ActionDef(type=action_type, arguments=arguments)

    @staticmethod
    def play_audio_effect(effect: str) -> ActionDef:
        return ActionFactory.create("play_audio_effect", effect=effect)

    @staticmethod
    def stop_audio() -> ActionDef:
        return ActionFactory.create("stop_audio")

    @staticmethod
    def schedule_event(event: str, delay_ms: int) -> ActionDef:
        return ActionFactory.create("schedule_event", event=event, delay_ms=delay_ms)


class WeaponProfileBuilder:
    def __init__(self) -> None:
        self._events: list[str] = []
        self._initial_state = "ready"
        self._states: dict[str, StateDef] = {}
        self._transitions: dict[str, TransitionDef] = {}
        self._clips: dict[str, ClipDef] = {}
        self._effects: dict[str, AudioEffectDef] = {}

    def set_events(self, events: list[str]) -> None:
        self._events = list(events)

    def set_initial_state(self, state_id: str) -> None:
        self._initial_state = state_id

    def ensure_state(self, state_id: str, label: str = "") -> StateDef:
        state = self._states.get(state_id)
        if state is None:
            state = StateDef(id=state_id, label=label or state_id)
            self._states[state_id] = state
        return state

    def add_transition(self, transition_id: str, source: str, trigger: str, target: str) -> TransitionDef:
        if transition_id in self._transitions:
            raise ValueError(f"Transition already exists: {transition_id}")
        transition = TransitionDef(id=transition_id, source=source, trigger=trigger, target=target)
        self._transitions[transition_id] = transition
        return transition

    def require_transition(self, transition_id: str) -> TransitionDef:
        return self._transitions[transition_id]

    def set_clip(self, name: str, path: str, preload: bool = True) -> None:
        self._clips[name] = ClipDef(name=name, path=path, preload=preload)

    def set_audio_effect(
        self,
        name: str,
        *,
        clips: list[str] | tuple[str, ...] | None = None,
        clip: str | None = None,
        mode: str = "once",
        interrupt: str = "interrupt",
        loop: bool = False,
        gain: float = 1.0,
    ) -> None:
        if clips is not None and clip is not None:
            raise ValueError("Specify clip or clips, not both")
        selected_clips = list(clips) if clips is not None else ([clip] if clip is not None else [])
        self._effects[name] = AudioEffectDef(
            name=name, clips=selected_clips, mode=mode, interrupt=interrupt, loop=loop, gain=gain
        )

    def append_transition_action(self, transition_id: str, action: ActionDef) -> None:
        self.require_transition(transition_id).actions.append(action)

    def remove_transition_actions_by_type(self, transition_id: str, action_type: str) -> None:
        actions = self.require_transition(transition_id).actions
        actions[:] = [action for action in actions if action.type != action_type]

    def append_state_entry_action(self, state_id: str, action: ActionDef) -> None:
        self._states[state_id].on_entry.append(action)

    def remove_state_entry_actions_by_type(self, state_id: str, action_type: str) -> None:
        actions = self._states[state_id].on_entry
        actions[:] = [action for action in actions if action.type != action_type]

    def append_state_exit_action(self, state_id: str, action: ActionDef) -> None:
        self._states[state_id].on_exit.append(action)

    def remove_state_exit_actions_by_type(self, state_id: str, action_type: str) -> None:
        actions = self._states[state_id].on_exit
        actions[:] = [action for action in actions if action.type != action_type]

    def build_gun(self) -> GunConfig:
        return GunConfig(events=list(self._events))

    def build_weapon(self) -> WeaponConfig:
        return WeaponConfig(
            initial_state=self._initial_state,
            states=dict(self._states),
            transitions=list(self._transitions.values()),
            clips=dict(self._clips),
            audio_effects=dict(self._effects),
        )
