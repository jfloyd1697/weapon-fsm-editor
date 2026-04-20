from pathlib import Path
from typing import Any

import yaml

from weapon_fsm_core.domain.model import (
    ActionDef,
    ClipDef,
    GunConfig,
    GuardDef,
    LightSequenceDef,
    ClipSetDef,
    StateDef,
    TransitionDef,
    WeaponConfig,
)


class ProfileRepository:
    def load_gun(self, path: str | Path) -> GunConfig:
        return self.load_gun_text(Path(path).read_text(encoding="utf-8"))

    def load_weapon(self, path: str | Path) -> WeaponConfig:
        source_path = Path(path)
        return self.load_weapon_text(source_path.read_text(encoding="utf-8"), source_path=source_path)

    def load_gun_text(self, text: str) -> GunConfig:
        raw = yaml.safe_load(text) or {}
        gun_raw = raw.get("gun", raw)

        event_ids: list[str] = []
        for item in gun_raw.get("events", []):
            if isinstance(item, dict):
                event_id = item.get("id")
            else:
                event_id = item
            if event_id:
                event_ids.append(str(event_id))

        return GunConfig(events=tuple(event_ids))

    def load_weapon_text(
        self,
        text: str,
        source_path: str | Path | None = None,
    ) -> WeaponConfig:
        raw = yaml.safe_load(text) or {}
        weapon_raw = raw.get("weapon", raw)
        states = self._parse_states(weapon_raw.get("states", []))
        transitions = self._parse_transitions(weapon_raw.get("transitions", []))
        variables = dict(weapon_raw.get("variables", {}))
        clips = self._parse_clips(raw.get("clips", weapon_raw.get("clips", {})))
        clip_sets = self._parse_clip_sets(raw.get("clip_sets", weapon_raw.get("clip_sets", {})))
        light_sequences = self._parse_light_sequences(
            raw.get("light_sequences", weapon_raw.get("light_sequences", {}))
        )

        initial_state = weapon_raw.get("initial_state", "ready")
        return WeaponConfig(
            initial_state=str(initial_state),
            variables=variables,
            states=states,
            transitions=tuple(transitions),
            clips=clips,
            clip_sets=clip_sets,
            light_sequences=light_sequences,
            source_path=Path(source_path) if source_path is not None else None,
        )

    def _parse_clips(self, raw_clips: dict[str, Any]) -> dict[str, ClipDef]:
        clips: dict[str, ClipDef] = {}
        for name, raw_clip in raw_clips.items():
            if isinstance(raw_clip, str):
                path = raw_clip
                preload = True
            else:
                path = str(raw_clip.get("path", ""))
                preload = bool(raw_clip.get("preload", True))
            clips[str(name)] = ClipDef(name=str(name), path=path, preload=preload)
        return clips


    def _parse_clip_sets(self, raw_clip_sets: dict[str, Any]) -> dict[str, ClipSetDef]:
        clip_sets: dict[str, ClipSetDef] = {}
        for name, raw_clip_set in raw_clip_sets.items():
            if isinstance(raw_clip_set, list):
                clips = tuple(str(item) for item in raw_clip_set)
                mode = "random"
            else:
                clips = tuple(str(item) for item in raw_clip_set.get("clips", []))
                mode = str(raw_clip_set.get("mode", "random"))
            clip_sets[str(name)] = ClipSetDef(name=str(name), clips=clips, mode=mode)
        return clip_sets

    def _parse_light_sequences(self, raw_sequences: dict[str, Any]) -> dict[str, LightSequenceDef]:
        sequences: dict[str, LightSequenceDef] = {}
        for name, raw_sequence in raw_sequences.items():
            if isinstance(raw_sequence, str):
                path = raw_sequence
                preload = True
            else:
                path = str(raw_sequence.get("path", ""))
                preload = bool(raw_sequence.get("preload", True))
            sequences[str(name)] = LightSequenceDef(name=str(name), path=path, preload=preload)
        return sequences

    def _parse_states(self, raw_states: list[dict[str, Any]]) -> dict[str, StateDef]:
        states: dict[str, StateDef] = {}

        for raw_state in raw_states:
            state = StateDef(
                id=str(raw_state["id"]),
                label=str(raw_state.get("label", raw_state["id"])),
                on_entry=self._parse_actions(raw_state.get("on_entry", [])),
                on_exit=self._parse_actions(raw_state.get("on_exit", [])),
            )
            states[state.id] = state

        return states

    def _parse_transitions(
        self,
        raw_transitions: list[dict[str, Any]],
    ) -> list[TransitionDef]:
        transitions: list[TransitionDef] = []

        for raw_transition in raw_transitions:
            transitions.append(
                TransitionDef(
                    id=str(raw_transition["id"]),
                    source=str(raw_transition["source"]),
                    trigger=str(raw_transition["trigger"]),
                    target=str(raw_transition["target"]),
                    guard=self._parse_guard(raw_transition.get("guard")),
                    actions=self._parse_actions(raw_transition.get("actions", [])),
                )
            )

        return transitions

    def _parse_actions(self, raw_actions: list[dict[str, Any]]) -> tuple[ActionDef, ...]:
        actions: list[ActionDef] = []

        for raw_action in raw_actions:
            action_type = str(raw_action["type"])
            arguments = {key: value for key, value in raw_action.items() if key != "type"}
            actions.append(ActionDef(type=action_type, arguments=arguments))

        return tuple(actions)

    def _parse_guard(self, raw: dict[str, Any] | None) -> GuardDef | None:
        if not raw:
            return None

        all_items = tuple(
            item for item in (self._parse_guard(entry) for entry in raw.get("all", [])) if item is not None
        )
        any_items = tuple(
            item for item in (self._parse_guard(entry) for entry in raw.get("any", [])) if item is not None
        )

        return GuardDef(
            all=all_items,
            any=any_items,
            trigger_pressed=raw.get("trigger_pressed"),
            var_eq=raw.get("var_eq"),
            var_gt=raw.get("var_gt"),
            var_gte=raw.get("var_gte"),
            var_lt=raw.get("var_lt"),
            var_lte=raw.get("var_lte"),
        )
