from pathlib import Path
from typing import Any

from weapon_fsm_core.domain.extensions import WeaponProfileExtensionData
from weapon_fsm_core.domain.model import LightSequenceDef, WeaponConfig

from ..domain.light_sequence import validate_light_sequence


class LightsProfileExtension:
    key = "lights"

    def load_weapon_node(self, node: Any, *, source_path: Path | None) -> WeaponProfileExtensionData:
        if not isinstance(node, dict):
            raise ValueError("lights must be a mapping")

        raw_sequences = node.get("sequences", node)
        if not isinstance(raw_sequences, dict):
            raise ValueError("lights.sequences must be a mapping")

        light_sequences: dict[str, LightSequenceDef] = {}
        for name, raw_sequence in raw_sequences.items():
            if isinstance(raw_sequence, str):
                path = raw_sequence
                preload = True
            elif isinstance(raw_sequence, dict):
                path = str(raw_sequence.get("path", ""))
                preload = bool(raw_sequence.get("preload", True))
            else:
                raise ValueError(f"lights.sequences.{name} must be a string or mapping")
            light_sequences[str(name)] = LightSequenceDef(name=str(name), path=path, preload=preload)

        return WeaponProfileExtensionData(
            values={"light_sequences": light_sequences, "subsystems": {self.key: node}},
            references={"light_sequences": set(light_sequences.keys())},
        )

    def validate_weapon_node(self, weapon: WeaponConfig, *, source_path: Path | None) -> list[tuple[str, str]]:
        issues: list[tuple[str, str]] = []
        subsystem = weapon.subsystems.get(self.key)
        if subsystem is None:
            return issues

        for name, sequence in weapon.light_sequences.items():
            if not sequence.path:
                issues.append((f"lights.sequences.{name}.path", "Light sequence path is required"))
                continue
            if source_path is None:
                continue
            resolved = Path(weapon.resolve_asset_path(sequence.path))
            if not resolved.exists():
                continue
            for message in validate_light_sequence(resolved):
                issues.append((f"lights.sequences.{name}.path", message))
        return issues
