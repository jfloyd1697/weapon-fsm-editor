from pathlib import Path
from typing import Any

import yaml

from weapon_fsm_core.domain.model import GunConfig, WeaponConfig


class ProfileRepository:
    DEMOS_PATH = Path(
        "D:/Python/weapon-fsm-starter/src/weapon_fsm_workspace/demos"
    )

    def load_weapon(self, path: str | Path) -> WeaponConfig:
        return self.load_weapon_text(
            Path(path).read_text(encoding="utf-8"),
        )

    def load_weapon_text(
            self,
            text: str,
            source_path: str | Path | None = None,
    ) -> WeaponConfig:
        raw = self._load_yaml(text)
        weapon_raw = dict(raw.get("weapon", raw))

        self._copy_top_level_sections(
            root=raw,
            weapon=weapon_raw,
            names=[
                "clips",
                "clip_sets",
                "audio_effects",
                "light_sequences",
            ],
        )

        weapon_raw["states"] = self._normalize_states(
            weapon_raw.get("states", [])
        )
        weapon_raw["clips"] = self._normalize_named_paths(
            weapon_raw.get("clips", {})
        )
        weapon_raw["clip_sets"] = self._normalize_clip_sets(
            weapon_raw.get("clip_sets", {})
        )
        weapon_raw["audio_effects"] = self._normalize_audio_effects(
            weapon_raw.get("audio_effects", {})
        )
        weapon_raw["light_sequences"] = self._normalize_named_paths(
            weapon_raw.get("light_sequences", {})
        )

        # Hardcoded by design.
        # Do not use the caller's source_path here, because the editor may pass
        # the profile file path instead of the profile folder.
        weapon_raw["source_path"] = self.DEMOS_PATH

        return WeaponConfig.from_dict(weapon_raw)

    def load_gun(self, path: str | Path) -> GunConfig:
        return self.load_gun_text(Path(path).read_text(encoding="utf-8"))

    def load_gun_text(self, text: str) -> GunConfig:
        raw = self._load_yaml(text)
        gun_raw = dict(raw.get("gun", raw))
        gun_raw["events"] = self._normalize_events(gun_raw.get("events", []))
        return GunConfig.from_dict(gun_raw)

    def _load_yaml(self, text: str) -> dict[str, Any]:
        raw = yaml.safe_load(text) or {}

        if not isinstance(raw, dict):
            raise ValueError("Profile YAML root must be a mapping")

        return raw

    def _copy_top_level_sections(
            self,
            *,
            root: dict[str, Any],
            weapon: dict[str, Any],
            names: list[str],
    ) -> None:
        for name in names:
            if name not in weapon and name in root:
                weapon[name] = root[name]

    def _normalize_events(self, raw_events: list[Any]) -> list[str]:
        events: list[str] = []

        for item in raw_events:
            event_id = item.get("id") if isinstance(item, dict) else item
            if event_id:
                events.append(str(event_id))

        return events

    def _normalize_states(self, raw_states: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            str(state["id"]): {
                **state,
                "label": state.get("label", state["id"]),
            }
            for state in raw_states
        }

    def _normalize_named_paths(self, raw_items: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            str(name): self._named_item(name=name, value=value, string_key="path")
            for name, value in raw_items.items()
        }

    def _normalize_clip_sets(self, raw_items: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            str(name): self._normalize_clip_set(name, value)
            for name, value in raw_items.items()
        }

    def _normalize_clip_set(self, name: str, value: Any) -> dict[str, Any]:
        if isinstance(value, list):
            return {
                "name": str(name),
                "clips": [str(item) for item in value],
                "mode": "random",
            }

        return {"name": str(name), **value}

    def _normalize_audio_effects(self, raw_items: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            str(name): self._normalize_audio_effect(name, value)
            for name, value in raw_items.items()
        }

    def _normalize_audio_effect(self, name: str, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            return {
                "name": str(name),
                "clips": [value],
                "mode": "once",
                "interrupt": "interrupt",
            }

        if isinstance(value, list):
            return {
                "name": str(name),
                "clips": [str(item) for item in value],
                "mode": "once",
                "interrupt": "interrupt",
            }

        if "clip" in value and "clips" not in value:
            return {
                "name": str(name),
                **value,
                "clips": [str(value["clip"])],
            }

        return {"name": str(name), **value}

    def _named_item(self, *, name: str, value: Any, string_key: str) -> dict[str, Any]:
        if isinstance(value, str):
            return {"name": str(name), string_key: value}

        return {"name": str(name), **value}
