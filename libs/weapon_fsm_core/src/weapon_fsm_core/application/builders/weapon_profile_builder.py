from pathlib import Path
from typing import Any

from weapon_fsm_core.domain.model import (
    ActionDef,
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
    def __init__(self):
        self._events: list[str] = []

        self._initial_state: str | None = None
        self._states: dict[str, StateDef] = {}
        self._transitions: list[TransitionDef] = []
        self._variables: dict[str, Any] = {}
        self._clips: dict[str, ClipDef] = {}
        self._clip_sets: dict[str, ClipSetDef] = {}
        self._light_sequences: dict[str, LightSequenceDef] = {}
        self._source_path: Path | None = None

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

    def ensure_state(self, state_id: str, label: str | None = None) -> "WeaponProfileBuilder":
        if state_id not in self._states:
            self._states[state_id] = StateDef(
                id=state_id,
                label=label or state_id,
                on_entry=(),
                on_exit=(),
            )
        elif label is not None:
            state = self._states[state_id]
            self._states[state_id] = StateDef(
                id=state.id,
                label=label,
                on_entry=state.on_entry,
                on_exit=state.on_exit,
            )
        return self

    def append_state_entry_action(
        self,
        state_id: str,
        action: ActionDef,
    ) -> "WeaponProfileBuilder":
        self.ensure_state(state_id)
        state = self._states[state_id]
        self._states[state_id] = StateDef(
            id=state.id,
            label=state.label,
            on_entry=state.on_entry + (action,),
            on_exit=state.on_exit,
        )
        return self

    def append_state_exit_action(
        self,
        state_id: str,
        action: ActionDef,
    ) -> "WeaponProfileBuilder":
        self.ensure_state(state_id)
        state = self._states[state_id]
        self._states[state_id] = StateDef(
            id=state.id,
            label=state.label,
            on_entry=state.on_entry,
            on_exit=state.on_exit + (action,),
        )
        return self

    def remove_state_entry_actions_by_type(
        self,
        state_id: str,
        action_type: str,
    ) -> "WeaponProfileBuilder":
        self.ensure_state(state_id)
        state = self._states[state_id]
        self._states[state_id] = StateDef(
            id=state.id,
            label=state.label,
            on_entry=tuple(action for action in state.on_entry if action.type != action_type),
            on_exit=state.on_exit,
        )
        return self

    def remove_state_exit_actions_by_type(
        self,
        state_id: str,
        action_type: str,
    ) -> "WeaponProfileBuilder":
        self.ensure_state(state_id)
        state = self._states[state_id]
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

    def append_transition_action(
        self,
        transition_id: str,
        action: ActionDef,
    ) -> "WeaponProfileBuilder":
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

    def remove_transition_actions_by_type(
        self,
        transition_id: str,
        action_type: str,
    ) -> "WeaponProfileBuilder":
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

    def set_transition_guard(
        self,
        transition_id: str,
        guard: GuardDef | None,
    ) -> "WeaponProfileBuilder":
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

    def set_clip(
        self,
        name: str,
        path: str,
        preload: bool = True,
    ) -> "WeaponProfileBuilder":
        self._clips[name] = ClipDef(name=name, path=path, preload=preload)
        return self

    def set_clip_set(
        self,
        name: str,
        clips: list[str] | tuple[str, ...],
        mode: str = "random",
    ) -> "WeaponProfileBuilder":
        self._clip_sets[name] = ClipSetDef(name=name, clips=tuple(clips), mode=mode)
        return self

    def set_light_sequence(
        self,
        name: str,
        path: str,
        preload: bool = True,
    ) -> "WeaponProfileBuilder":
        self._light_sequences[name] = LightSequenceDef(
            name=name,
            path=path,
            preload=preload,
        )
        return self

    def build_gun(self) -> GunConfig:
        return GunConfig(events=tuple(self._events))

    def build_weapon(self) -> WeaponConfig:
        if self._initial_state is None:
            raise ValueError("initial_state has not been set")
        return WeaponConfig(
            initial_state=self._initial_state,
            states=dict(self._states),
            transitions=tuple(self._transitions),
            variables=dict(self._variables),
            clips=dict(self._clips),
            clip_sets=dict(self._clip_sets),
            light_sequences=dict(self._light_sequences),
            source_path=self._source_path,
        )