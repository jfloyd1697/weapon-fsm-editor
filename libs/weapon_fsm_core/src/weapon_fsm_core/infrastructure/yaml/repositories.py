from pathlib import Path
from typing import Any

import yaml

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

from .profile_schema import ActionFile, ClipFile, ClipSetFile, EventFile, GuardFile, GunFile, LightSequenceFile, StateFile, TransitionFile, WeaponProfileFile


class ProfileRepository:
    def load_gun(self, path: str | Path) -> GunConfig:
        return self.load_gun_text(Path(path).read_text(encoding="utf-8"))

    def load_weapon(self, path: str | Path) -> WeaponConfig:
        source_path = Path(path)
        text = source_path.read_text(encoding="utf-8")
        return self.load_weapon_text(text, source_path)

    def load_gun_text(self, text: str) -> GunConfig:
        raw = yaml.safe_load(text) or {}
        gun_file = GunFile.from_dict(self._normalize_gun_profile(raw))
        return GunConfig(
            events=tuple(
                event.id if isinstance(event, EventFile) else str(event)
                for event in gun_file.events
            )
        )

    def load_weapon_text(
        self,
        text: str,
        source_path: str | Path | None = None,
    ) -> WeaponConfig:
        profile = WeaponProfileFile.from_yaml(text)
        weapon_profile = profile.weapon.to_dict()
        weapon_profile["source_path"] = source_path.as_posix()
        return WeaponConfig.from_dict(weapon_profile)

    def _normalize_gun_profile(self, raw: dict[str, Any]) -> dict[str, Any]:
        gun_raw = dict(raw.get("gun", raw) or {})
        events = []
        for item in gun_raw.get("events", []):
            if isinstance(item, dict):
                events.append(item)
            else:
                events.append({"id": str(item)})
        gun_raw["events"] = events
        return gun_raw

    def _normalize_weapon_profile(self, raw: dict[str, Any]) -> dict[str, Any]:
        if "weapon" not in raw:
            raw = {"weapon": raw}

        weapon_raw = dict(raw.get("weapon") or {})
        profile_raw = dict(raw)
        for key in ("clips", "clip_sets", "light_sequences"):
            value = profile_raw.get(key)
            if value is None and key in weapon_raw:
                value = weapon_raw.pop(key)
            profile_raw[key] = self._normalize_asset_mapping(key, value or {})
        profile_raw["weapon"] = weapon_raw
        return profile_raw

    def _normalize_asset_mapping(self, kind: str, raw_mapping: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for name, value in raw_mapping.items():
            if kind == "clips":
                if isinstance(value, str):
                    normalized[name] = {"path": value}
                else:
                    normalized[name] = value
                continue

            if kind == "clip_sets":
                if isinstance(value, list):
                    normalized[name] = {"clips": value, "mode": "random"}
                else:
                    normalized[name] = value
                continue

            if kind == "light_sequences":
                if isinstance(value, str):
                    normalized[name] = {"path": value}
                else:
                    normalized[name] = value
                continue

        return normalized

    def _clip_to_model(self, name: str, clip: ClipFile) -> ClipDef:
        return ClipDef.from_dict({
            "name": name,
            "path": clip.path,
            "preload": clip.preload,
        })

    def _clip_set_to_model(self, name: str, clip_set: ClipSetFile) -> ClipSetDef:
        return ClipSetDef.from_dict({
            "name": name,
            "clips": clip_set.clips,
            "mode": clip_set.mode,
        })

    def _light_sequence_to_model(self, name: str, sequence: LightSequenceFile) -> LightSequenceDef:
        return LightSequenceDef.from_dict({
            "name": name,
            "path": sequence.path,
            "preload": sequence.preload,
        })

    def _state_to_model(self, state: StateFile) -> StateDef:
        return StateDef.from_dict({
            "id": state.id,
            "label": state.label,
            "on_entry": [self._action_to_model(action) for action in state.on_entry],
            "on_exit": [self._action_to_model(action) for action in state.on_exit],
        })

    def _transition_to_model(self, transition: TransitionFile) -> TransitionDef:
        return TransitionDef.from_dict({
            "id": transition.id,
            "source": transition.source,
            "trigger": transition.trigger,
            "target": transition.target,
            "guard": self._guard_to_model(transition.guard),
            "actions": [self._action_to_model(action) for action in transition.actions],
        })

    def _action_to_model(self, action: ActionFile) -> ActionDef:
        arguments = dict(action.arguments)
        for name in (
            "sound",
            "clip",
            "clips",
            "clip_set",
            "pattern",
            "sequence",
            "event",
            "delay_ms",
            "delta",
            "value",
            "interrupt",
            "mode",
        ):
            value = getattr(action, name)
            if value is None:
                continue
            if name == "clips" and value == []:
                continue
            arguments[name] = value

        return ActionDef.from_dict({
            "type": action.type,
            "arguments": arguments,
        })

    def _guard_to_model(self, guard: GuardFile | None) -> GuardDef | None:
        if guard is None:
            return None

        return GuardDef.from_dict({
            "all": [self._guard_to_model(item) for item in guard.all],
            "any": [self._guard_to_model(item) for item in guard.any],
            "trigger_pressed": guard.trigger_pressed,
            "var_gt": self._guard_compare("ammo", guard.ammo_gt),
            "var_gte": self._guard_compare("ammo", guard.ammo_gte),
            "var_eq": self._guard_compare("ammo", guard.ammo_eq),
            "var_lt": self._guard_compare("ammo", guard.ammo_lt),
            "var_lte": self._guard_compare("ammo", guard.ammo_lte),
        })

    def _guard_compare(self, name: str, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return {"name": name, "value": value}
