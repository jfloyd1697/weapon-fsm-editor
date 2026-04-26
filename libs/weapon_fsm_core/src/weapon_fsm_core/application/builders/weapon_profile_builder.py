from pathlib import Path
from typing import Any

from weapon_fsm_core.domain.model import (
    ActionDef,
    AudioEffectDef,
    ClipDef,
    ClipSetDef,
    GunConfig,
    GuardDef,
    LightSequenceDef,
    StateDef,
    TransitionDef,
    WeaponConfig,
)


class WeaponProfileBuilder:
    def __init__(self, gun: GunConfig | None = None, weapon: WeaponConfig | None = None):
        self._events = list(gun.events) if gun is not None else []
        self._initial_state = weapon.initial_state if weapon is not None else None
        self._variables = dict(weapon.variables) if weapon is not None else {}
        self._states = dict(weapon.states) if weapon is not None else {}
        self._transitions = list(weapon.transitions) if weapon is not None else []
        self._clips = dict(weapon.clips) if weapon is not None else {}
        self._clip_sets = dict(weapon.clip_sets) if weapon is not None else {}
        self._audio_effects = dict(weapon.audio_effects) if weapon is not None else {}
        self._light_sequences = dict(weapon.light_sequences) if weapon is not None else {}
        self._source_path = weapon.source_path if weapon is not None else None

    def set_source_path(self, path: str | Path | None) -> "WeaponProfileBuilder":
        self._source_path = None if path is None else Path(path)
        return self

    def set_events(self, events: list[str] | tuple[str, ...]) -> "WeaponProfileBuilder":
        self._events = list(events)
        return self

    def add_event(self, event: str) -> "WeaponProfileBuilder":
        if event not in self._events:
            self._events.append(event)
        return self

    def set_initial_state(self, state_id: str) -> "WeaponProfileBuilder":
        self._initial_state = state_id
        return self

    def set_variable(self, name: str, value: Any) -> "WeaponProfileBuilder":
        self._variables[name] = value
        return self

    def ensure_state(self, state_id: str, label: str | None = None) -> StateDef:
        state = self._states.get(state_id)
        if state is None:
            state = StateDef(id=state_id, label=label or state_id)
        elif label is not None:
            state = StateDef(id=state.id, label=label, on_entry=state.on_entry, on_exit=state.on_exit)
        self._states[state_id] = state
        return state

    def append_state_entry_action(self, state_id: str, action: ActionDef) -> "WeaponProfileBuilder":
        state = self.ensure_state(state_id)
        self._states[state_id] = StateDef(
            id=state.id,
            label=state.label,
            on_entry=state.on_entry + (action,),
            on_exit=state.on_exit,
        )
        return self

    def append_state_exit_action(self, state_id: str, action: ActionDef) -> "WeaponProfileBuilder":
        state = self.ensure_state(state_id)
        self._states[state_id] = StateDef(
            id=state.id,
            label=state.label,
            on_entry=state.on_entry,
            on_exit=state.on_exit + (action,),
        )
        return self

    def remove_state_entry_actions_by_type(self, state_id: str, action_type: str) -> "WeaponProfileBuilder":
        state = self.ensure_state(state_id)
        self._states[state_id] = StateDef(
            id=state.id,
            label=state.label,
            on_entry=tuple(action for action in state.on_entry if action.type != action_type),
            on_exit=state.on_exit,
        )
        return self

    def remove_state_exit_actions_by_type(self, state_id: str, action_type: str) -> "WeaponProfileBuilder":
        state = self.ensure_state(state_id)
        self._states[state_id] = StateDef(
            id=state.id,
            label=state.label,
            on_entry=state.on_entry,
            on_exit=tuple(action for action in state.on_exit if action.type != action_type),
        )
        return self

    def add_transition(
        self,
        transition_id: str,
        source: str,
        trigger: str,
        target: str,
        guard: GuardDef | None = None,
    ) -> "WeaponProfileBuilder":
        self._transitions.append(
            TransitionDef(
                id=transition_id,
                source=source,
                trigger=trigger,
                target=target,
                guard=guard,
                actions=(),
            )
        )
        return self

    def _find_transition_index(self, transition_id: str) -> int:
        for index, transition in enumerate(self._transitions):
            if transition.id == transition_id:
                return index
        raise KeyError("Unknown transition: {0}".format(transition_id))

    def append_transition_action(self, transition_id: str, action: ActionDef) -> "WeaponProfileBuilder":
        index = self._find_transition_index(transition_id)
        transition = self._transitions[index]
        self._transitions[index] = TransitionDef(
            id=transition.id,
            source=transition.source,
            trigger=transition.trigger,
            target=transition.target,
            guard=transition.guard,
            actions=transition.actions + (action,),
        )
        return self

    def remove_transition_actions_by_type(self, transition_id: str, action_type: str) -> "WeaponProfileBuilder":
        index = self._find_transition_index(transition_id)
        transition = self._transitions[index]
        self._transitions[index] = TransitionDef(
            id=transition.id,
            source=transition.source,
            trigger=transition.trigger,
            target=transition.target,
            guard=transition.guard,
            actions=tuple(action for action in transition.actions if action.type != action_type),
        )
        return self

    def set_transition_guard(self, transition_id: str, guard: GuardDef | None) -> "WeaponProfileBuilder":
        index = self._find_transition_index(transition_id)
        transition = self._transitions[index]
        self._transitions[index] = TransitionDef(
            id=transition.id,
            source=transition.source,
            trigger=transition.trigger,
            target=transition.target,
            guard=guard,
            actions=transition.actions,
        )
        return self

    def set_clip(self, name: str, path: str, preload: bool = True) -> "WeaponProfileBuilder":
        self._clips[name] = ClipDef(name=name, path=path, preload=preload)
        return self

    def set_clip_set(self, name: str, clips: list[str] | tuple[str, ...], mode: str = "random") -> "WeaponProfileBuilder":
        self._clip_sets[name] = ClipSetDef(name=name, clips=tuple(clips), mode=mode)
        return self

    def set_audio_effect(
        self,
        name: str,
        *,
        clips: list[str] | tuple[str, ...] | None = None,
        clip: str | None = None,
        mode: str = "one_shot",
        interrupt: str = "interrupt",
        loop: bool = False,
        gain: float = 1.0,
    ) -> "WeaponProfileBuilder":
        resolved_clips = list(clips) if clips is not None else ([clip] if clip is not None else [])
        self._audio_effects[name] = AudioEffectDef(
            name=name,
            clips=tuple(resolved_clips),
            mode=mode,
            interrupt=interrupt,
            loop=loop,
            gain=gain,
        )
        return self

    def set_light_sequence(self, name: str, path: str, preload: bool = True) -> "WeaponProfileBuilder":
        self._light_sequences[name] = LightSequenceDef(name=name, path=path, preload=preload)
        return self

    def build_gun(self) -> GunConfig:
        return GunConfig(events=tuple(self._events))

    def build_weapon(self) -> WeaponConfig:
        if self._initial_state is None:
            raise ValueError("initial_state has not been set")
        return WeaponConfig(
            initial_state=self._initial_state,
            variables=dict(self._variables),
            states=dict(self._states),
            transitions=tuple(self._transitions),
            clips=dict(self._clips),
            clip_sets=dict(self._clip_sets),
            audio_effects=dict(self._audio_effects),
            light_sequences=dict(self._light_sequences),
            source_path=self._source_path,
        )
