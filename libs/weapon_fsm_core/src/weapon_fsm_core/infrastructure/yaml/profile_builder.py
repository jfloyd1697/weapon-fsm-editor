from typing import Any

import yaml

from weapon_fsm_core.domain.model import ActionDef, ClipDef, ClipSetDef, GuardDef, GunConfig, LightSequenceDef, StateDef, TransitionDef, WeaponConfig
from weapon_fsm_core.infrastructure.yaml import ProfileYamlMapper
from weapon_fsm_core.infrastructure.yaml.profile_schema import WeaponProfileFile


class ProfileYamlBuilder:
    def dump_gun(self, gun: GunConfig) -> str:
        root = {
            "gun": {
                "events": [self._build_event(event_id) for event_id in gun.events],
            }
        }
        return self._dump_yaml(root)

    def dump_weapon(self, weapon: WeaponConfig) -> str:
        return ProfileYamlMapper.weapon_to_text(weapon)

        # clips = self._build_clips(weapon.clips)
        # if clips:
        #     root["clips"] = clips
        #
        # clip_sets = self._build_clip_sets(weapon.clip_sets)
        # if clip_sets:
        #     root["clip_sets"] = clip_sets
        #
        # light_sequences = self._build_light_sequences(weapon.light_sequences)
        # if light_sequences:
        #     root["light_sequences"] = light_sequences
        #
        # weapon_node: dict[str, Any] = {
        #     "initial_state": weapon.initial_state,
        #     "states": [self._build_state(state) for state in weapon.states],
        #     "transitions": [self._build_transition(transition) for transition in weapon.transitions],
        # }
        # if weapon.variables:
        #     weapon_node["variables"] = dict(weapon.variables)
        #
        # root["weapon"] = weapon_node
        # return self._dump_yaml(root)

    def _build_event(self, event_id: str) -> dict[str, Any]:
        return {"id": event_id}

    def _build_clips(self, clips: dict[str, ClipDef]) -> dict[str, Any]:
        node: dict[str, Any] = {}
        for name, clip in clips.items():
            if clip.preload:
                node[name] = clip.path
            else:
                node[name] = {
                    "path": clip.path,
                    "preload": clip.preload,
                }
        return node

    def _build_light_sequences(self, sequences: dict[str, LightSequenceDef]) -> dict[str, Any]:
        node: dict[str, Any] = {}
        for name, sequence in sequences.items():
            if sequence.preload:
                node[name] = sequence.path
            else:
                node[name] = {
                    "path": sequence.path,
                    "preload": sequence.preload,
                }
        return node

    def _build_clip_sets(self, clip_sets: dict[str, ClipSetDef]) -> dict[str, Any]:
        node: dict[str, Any] = {}
        for name, clip_set in clip_sets.items():
            if clip_set.mode == "random":
                node[name] = list(clip_set.clips)
            else:
                node[name] = {
                    "clips": list(clip_set.clips),
                    "mode": clip_set.mode,
                }
        return node

    def _build_state(self, state: StateDef) -> dict[str, Any]:
        node: dict[str, Any] = {"id": state.id}
        if state.label != state.id:
            node["label"] = state.label
        if state.on_entry:
            node["on_entry"] = [self._build_action(action) for action in state.on_entry]
        if state.on_exit:
            node["on_exit"] = [self._build_action(action) for action in state.on_exit]
        return node

    def _build_transition(self, transition: TransitionDef) -> dict[str, Any]:
        node: dict[str, Any] = {
            "id": transition.id,
            "source": transition.source,
            "target": transition.target,
            "trigger": transition.trigger,
        }
        if transition.guard is not None:
            node["guard"] = self._build_guard(transition.guard)
        if transition.actions:
            node["actions"] = [self._build_action(action) for action in transition.actions]
        return node

    def _build_guard(self, guard: GuardDef) -> dict[str, Any]:
        node: dict[str, Any] = {}
        if guard.trigger_pressed is not None:
            node["trigger_pressed"] = guard.trigger_pressed
        if guard.var_eq is not None:
            node["var_eq"] = dict(guard.var_eq)
        if guard.var_gt is not None:
            node["var_gt"] = dict(guard.var_gt)
        if guard.var_gte is not None:
            node["var_gte"] = dict(guard.var_gte)
        if guard.var_lt is not None:
            node["var_lt"] = dict(guard.var_lt)
        if guard.var_lte is not None:
            node["var_lte"] = dict(guard.var_lte)
        if guard.all:
            node["all"] = [self._build_guard(item) for item in guard.all]
        if guard.any:
            node["any"] = [self._build_guard(item) for item in guard.any]
        return node

    def _build_action(self, action: ActionDef) -> dict[str, Any]:
        node: dict[str, Any] = {"type": action.type}
        for key, value in action.arguments.items():
            if self._should_skip(value):
                continue
            node[key] = self._normalize_value(value)
        return node

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, tuple):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, list):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self._normalize_value(item) for key, item in value.items() if not self._should_skip(item)}
        return value

    def _should_skip(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, tuple, dict)) and not value:
            return True
        return False

    def _dump_yaml(self, payload: dict[str, Any]) -> str:
        return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
