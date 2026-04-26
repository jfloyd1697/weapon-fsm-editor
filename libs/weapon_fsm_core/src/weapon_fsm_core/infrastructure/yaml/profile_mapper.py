from pathlib import Path
from typing import Any

import yaml

from weapon_fsm_core.domain.model import GunConfig, WeaponConfig
from weapon_fsm_core.infrastructure.yaml.profile_schema import (
    ActionFile,
    ClipFile,
    ClipSetFile,
    EventFile,
    GuardFile,
    LightSequenceFile,
    StateFile,
    TransitionFile,
    WeaponFile,
    WeaponProfileFile,
)


class ProfileYamlMapper:
    @staticmethod
    def gun_to_data(gun: GunConfig) -> dict[str, Any]:
        events = [EventFile(id=event_id) for event_id in gun.events]
        return _strip_empty({"gun": {"events": [_event_to_data(event) for event in events]}})

    @staticmethod
    def weapon_to_data(weapon: WeaponConfig) -> dict[str, Any]:
        profile = WeaponProfileFile(
            weapon=WeaponFile(
                initial_state=weapon.initial_state,
                variables=dict(weapon.variables),
                states=[_state_to_file(state) for state in weapon.states.values()],
                transitions=[_transition_to_file(transition) for transition in weapon.transitions],
            ),
            clips={
                name: ClipFile(path=clip.path, preload=clip.preload)
                for name, clip in weapon.clips.items()
            },
            clip_sets={
                name: ClipSetFile(clips=list(clip_set.clips), mode=clip_set.mode)
                for name, clip_set in weapon.clip_sets.items()
            },
            light_sequences={
                name: LightSequenceFile(path=sequence.path, preload=sequence.preload)
                for name, sequence in weapon.light_sequences.items()
            },
        )

        data = {
            "weapon": {
                "initial_state": profile.weapon.initial_state,
                "variables": dict(profile.weapon.variables),
                "states": [_state_file_to_data(state) for state in profile.weapon.states],
                "transitions": [
                    _transition_file_to_data(transition) for transition in profile.weapon.transitions
                ],
            },
            "clips": {name: _clip_to_data(clip) for name, clip in profile.clips.items()},
            "clip_sets": {
                name: _clip_set_to_data(clip_set) for name, clip_set in profile.clip_sets.items()
            },
            "light_sequences": {
                name: _light_sequence_to_data(sequence)
                for name, sequence in profile.light_sequences.items()
            },
        }
        return _strip_empty(data)

    @staticmethod
    def gun_to_yaml(gun: GunConfig) -> str:
        return yaml.safe_dump(ProfileYamlMapper.gun_to_data(gun), sort_keys=False)

    @staticmethod
    def weapon_to_yaml(weapon: WeaponConfig) -> str:
        return yaml.safe_dump(ProfileYamlMapper.weapon_to_data(weapon), sort_keys=False)

    @staticmethod
    def write_gun(gun: GunConfig, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.write_text(ProfileYamlMapper.gun_to_yaml(gun), encoding="utf-8")
        return output_path

    @staticmethod
    def write_weapon(weapon: WeaponConfig, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.write_text(ProfileYamlMapper.weapon_to_yaml(weapon), encoding="utf-8")
        return output_path


def _state_to_file(state) -> StateFile:
    return StateFile(
        id=state.id,
        label=state.label,
        on_entry=[_action_to_file(action) for action in state.on_entry],
        on_exit=[_action_to_file(action) for action in state.on_exit],
    )


def _transition_to_file(transition) -> TransitionFile:
    return TransitionFile(
        id=transition.id,
        source=transition.source,
        target=transition.target,
        trigger=transition.trigger,
        actions=[_action_to_file(action) for action in transition.actions],
        guard=_guard_to_file(transition.guard),
    )


def _action_to_file(action) -> ActionFile:
    return ActionFile(type=action.type, arguments=dict(action.arguments))


def _guard_to_file(guard) -> GuardFile | None:
    if guard is None:
        return None
    return GuardFile(
        trigger_pressed=guard.trigger_pressed,
        all=[item for item in (_guard_to_file(entry) for entry in guard.all) if item is not None],
        any=[item for item in (_guard_to_file(entry) for entry in guard.any) if item is not None],
    )


def _state_file_to_data(state: StateFile) -> dict[str, Any]:
    return _strip_empty(
        {
            "id": state.id,
            "label": state.label,
            "on_entry": [_action_file_to_data(action) for action in state.on_entry],
            "on_exit": [_action_file_to_data(action) for action in state.on_exit],
        }
    )


def _transition_file_to_data(transition: TransitionFile) -> dict[str, Any]:
    return _strip_empty(
        {
            "id": transition.id,
            "source": transition.source,
            "target": transition.target,
            "trigger": transition.trigger,
            "actions": [_action_file_to_data(action) for action in transition.actions],
            "guard": _guard_file_to_data(transition.guard),
        }
    )


def _action_file_to_data(action: ActionFile) -> dict[str, Any]:
    data: dict[str, Any] = {"type": action.type}
    data.update(dict(action.arguments))
    return _strip_empty(data)


def _guard_file_to_data(guard: GuardFile | None) -> dict[str, Any] | None:
    if guard is None:
        return None
    return _strip_empty(
        {
            "trigger_pressed": guard.trigger_pressed,
            "all": [_guard_file_to_data(item) for item in guard.all],
            "any": [_guard_file_to_data(item) for item in guard.any],
        }
    )


def _event_to_data(event: EventFile) -> dict[str, Any] | str:
    if event.kind == "external" and event.label in (None, event.id):
        return event.id
    return _strip_empty({"id": event.id, "label": event.label, "kind": event.kind})


def _clip_to_data(clip: ClipFile) -> dict[str, Any] | str:
    if clip.preload:
        return clip.path
    return _strip_empty({"path": clip.path, "preload": clip.preload})


def _clip_set_to_data(clip_set: ClipSetFile) -> dict[str, Any] | list[str]:
    if clip_set.mode == "random":
        return list(clip_set.clips)
    return _strip_empty({"clips": list(clip_set.clips), "mode": clip_set.mode})


def _light_sequence_to_data(sequence: LightSequenceFile) -> dict[str, Any] | str:
    if sequence.preload:
        return sequence.path
    return _strip_empty({"path": sequence.path, "preload": sequence.preload})


def _strip_empty(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if item in (None, (), [], {}):
                continue
            stripped = _strip_empty(item)
            if stripped in (None, (), [], {}):
                continue
            cleaned[key] = stripped
        return cleaned

    if isinstance(value, list):
        cleaned_list = []
        for item in value:
            stripped = _strip_empty(item)
            if stripped in (None, (), [], {}):
                continue
            cleaned_list.append(stripped)
        return cleaned_list

    return value
