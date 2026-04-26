from dataclasses import MISSING, fields, is_dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from .profile_schema import (
    ActionFile,
    AudioEffectFile,
    ClipFile,
    GuardFile,
    StateFile,
    TransitionFile,
    WeaponProfileFile,
)


class WeaponProfileBuilder:
    def __init__(self, profile: WeaponProfileFile | None = None):
        self._profile = profile or WeaponProfileFile()

    @classmethod
    def from_yaml(cls, text: str) -> "WeaponProfileBuilder":
        return cls(WeaponProfileFile.from_yaml(text))

    @classmethod
    def from_file(cls, path: str | Path) -> "WeaponProfileBuilder":
        path_obj = Path(path)
        return cls.from_yaml(path_obj.read_text(encoding="utf-8"))

    @property
    def profile(self) -> WeaponProfileFile:
        return self._profile

    def set_initial_state(self, state_id: str) -> "WeaponProfileBuilder":
        self._profile.weapon.initial_state = state_id
        return self

    def set_variable(self, name: str, value: Any) -> "WeaponProfileBuilder":
        self._profile.weapon.variables[name] = value
        return self

    def set_audio_clip(
        self,
        name: str,
        path: str,
        preload: bool = True,
    ) -> "WeaponProfileBuilder":
        self._profile.audio.clips[name] = ClipFile(path=path, preload=preload)
        return self

    def remove_audio_clip(self, name: str) -> "WeaponProfileBuilder":
        self._profile.audio.clips.pop(name, None)
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
        if clips is None:
            clips = []
        normalized_clips = [str(item) for item in clips]
        if clip is not None:
            normalized_clips = [clip]
        self._profile.audio.effects[name] = AudioEffectFile(
            clips=normalized_clips,
            mode=mode,
            interrupt=interrupt,
            loop=loop,
            gain=gain,
        )
        return self

    def remove_audio_effect(self, name: str) -> "WeaponProfileBuilder":
        self._profile.audio.effects.pop(name, None)
        return self

    def ensure_state(self, state_id: str, label: str | None = None) -> StateFile:
        existing = self._find_state(state_id)
        if existing is not None:
            if label is not None:
                existing.label = label
            return existing

        state = StateFile(id=state_id, label=label or state_id)
        self._profile.weapon.states.append(state)
        return state

    def set_transition(
        self,
        transition_id: str,
        *,
        source: str,
        target: str,
        trigger: str,
        actions: list[ActionFile] | None = None,
        guard: GuardFile | None = None,
    ) -> TransitionFile:
        transition = self._find_transition(transition_id)
        if transition is None:
            transition = TransitionFile(
                id=transition_id,
                source=source,
                target=target,
                trigger=trigger,
            )
            self._profile.weapon.transitions.append(transition)
        transition.source = source
        transition.target = target
        transition.trigger = trigger
        transition.actions = list(actions or [])
        transition.guard = guard
        return transition

    def set_transition_actions(
        self,
        transition_id: str,
        actions: list[ActionFile],
    ) -> "WeaponProfileBuilder":
        transition = self._require_transition(transition_id)
        transition.actions = list(actions)
        return self

    def append_transition_action(
        self,
        transition_id: str,
        action: ActionFile,
    ) -> "WeaponProfileBuilder":
        transition = self._require_transition(transition_id)
        transition.actions.append(action)
        return self

    def set_state_entry_actions(
        self,
        state_id: str,
        actions: list[ActionFile],
    ) -> "WeaponProfileBuilder":
        state = self.ensure_state(state_id)
        state.on_entry = list(actions)
        return self

    def append_state_entry_action(
        self,
        state_id: str,
        action: ActionFile,
    ) -> "WeaponProfileBuilder":
        state = self.ensure_state(state_id)
        state.on_entry.append(action)
        return self

    def set_state_exit_actions(
        self,
        state_id: str,
        actions: list[ActionFile],
    ) -> "WeaponProfileBuilder":
        state = self.ensure_state(state_id)
        state.on_exit = list(actions)
        return self

    def append_state_exit_action(
        self,
        state_id: str,
        action: ActionFile,
    ) -> "WeaponProfileBuilder":
        state = self.ensure_state(state_id)
        state.on_exit.append(action)
        return self

    def to_dict(self) -> dict[str, Any]:
        compacted = _compact(self._profile)
        if not isinstance(compacted, dict):
            return {}
        return compacted

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    def write(self, path: str | Path) -> Path:
        path_obj = Path(path)
        path_obj.write_text(self.to_yaml(), encoding="utf-8")
        return path_obj

    def clone(self) -> "WeaponProfileBuilder":
        copied = WeaponProfileFile.from_dict(self.to_dict())
        return WeaponProfileBuilder(copied)

    def _find_state(self, state_id: str) -> StateFile | None:
        for state in self._profile.weapon.states:
            if state.id == state_id:
                return state
        return None

    def _find_transition(self, transition_id: str) -> TransitionFile | None:
        for transition in self._profile.weapon.transitions:
            if transition.id == transition_id:
                return transition
        return None

    def _require_transition(self, transition_id: str) -> TransitionFile:
        transition = self._find_transition(transition_id)
        if transition is None:
            raise KeyError("Unknown transition: %s" % transition_id)
        return transition


class ActionBuilder:
    @staticmethod
    def play_audio_effect(effect: str) -> ActionFile:
        return ActionFile(type="play_audio_effect", effect=effect)

    @staticmethod
    def play_audio(
        clip: str,
        mode: str = "one_shot",
        interrupt: str = "interrupt",
    ) -> ActionFile:
        return ActionFile(
            type="play_audio",
            clip=clip,
            mode=mode,
            interrupt=interrupt,
        )

    @staticmethod
    def stop_audio() -> ActionFile:
        return ActionFile(type="stop_audio")

    @staticmethod
    def dispatch_event(event: str) -> ActionFile:
        return ActionFile(type="dispatch_event", event=event)


def _compact(value: Any) -> Any:
    if is_dataclass(value):
        result: dict[str, Any] = {}
        for field_info in fields(value):
            current = getattr(value, field_info.name)
            compacted = _compact(current)
            if _should_skip_field(field_info, compacted):
                continue
            result[field_info.name] = compacted
        return result

    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            compacted = _compact(item)
            if _is_empty(compacted):
                continue
            result[key] = compacted
        return result

    if isinstance(value, list):
        return [item for item in (_compact(entry) for entry in value) if not _is_empty(item)]

    return value


def _should_skip_field(field_info: Any, compacted: Any) -> bool:
    if compacted is None:
        return True
    if _is_empty(compacted):
        return True
    if field_info.default is not MISSING:
        default_value = _compact(field_info.default)
        if compacted == default_value:
            return True
    if field_info.default_factory is not MISSING:
        default_value = _compact(field_info.default_factory())
        if compacted == default_value:
            return True
    return False


def _is_empty(value: Any) -> bool:
    return value == {} or value == []
