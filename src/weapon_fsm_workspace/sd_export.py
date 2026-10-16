from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from weapon_fsm_core.domain.model import ActionDef, GuardDef, WeaponConfig
from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository
from weapon_fsm_lights.domain.compiler import compile_animation
from weapon_fsm_lights.infrastructure.animation_loader import load_canvas_animation_sequence
from weapon_fsm_lights.infrastructure.authored_project_io import load_authored_project, load_project_layout
from weapon_fsm_lights.infrastructure.loader import load_light_sequence
from weapon_fsm_workspace.audio_export import export_audio_wav
from weapon_fsm_workspace.runtime_validation import normalize_action_payload, normalize_runtime_payload, validate_runtime_payload
from weapon_fsm_workspace.runtime_binary import encode_runtime
from weapon_fsm_workspace.compiled_assets import (
    encode_layout, encode_manifest, encode_sequence, decode_manifest,
)


MANIFEST_RELATIVE_PATH = Path("assets/weapons/weapons_manifest.bin")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    if not slug:
        raise ValueError("Weapon and bank names must contain at least one usable character")
    return slug


def _action_payload(action: ActionDef) -> dict[str, Any]:
    return normalize_action_payload(action.type, action.arguments)


def _guard_payload(guard: GuardDef) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if guard.all:
        payload["all"] = [_guard_payload(item) for item in guard.all]
    if guard.any:
        payload["any"] = [_guard_payload(item) for item in guard.any]
    for name in ("trigger_pressed", "var_eq", "var_gt", "var_gte", "var_lt", "var_lte"):
        value = getattr(guard, name)
        if value is not None:
            payload[name] = value
    return payload


class SdCardExporter:
    @staticmethod
    def weapon_directory(bank_name: str, weapon_name: str) -> Path:
        """Paths encoded into weapon.bin are relative to the MCU's SD root."""
        return Path("assets/weapons") / _slug(bank_name) / _slug(weapon_name)

    @classmethod
    def compiled_audio_path(cls, bank_name: str, weapon_name: str, clip_name: str) -> Path:
        return cls.weapon_directory(bank_name, weapon_name) / "audio" / f"{_slug(clip_name)}.wav"

    @classmethod
    def compiled_light_path(cls, bank_name: str, weapon_name: str, sequence_name: str) -> Path:
        return cls.weapon_directory(bank_name, weapon_name) / "lights" / f"{_slug(sequence_name)}.bin"

    def __init__(self, sd_root: str | Path) -> None:
        self.sd_root = Path(sd_root).expanduser().resolve()
        self.repository = ProfileRepository()

    def export_weapon(
        self,
        profile_path: str | Path,
        *,
        bank_name: str,
        weapon_name: str | None = None,
    ) -> Path:
        source = Path(profile_path).expanduser().resolve()
        assets_root = self.repository.asset_root_for_profile(source)
        weapon = self.repository.load_weapon_text(
            source.read_text(encoding="utf-8"),
            source_path=assets_root,
        )
        name = weapon_name or source.stem
        weapon_dir = self.sd_root / self.weapon_directory(bank_name, name)
        # Validate before converting audio or modifying any files on the SD card.
        # The compiled payload uses the same named references as the source.
        preflight = normalize_runtime_payload(self._build_runtime_payload(
            weapon,
            {name: clip.path for name, clip in weapon.clips.items()},
            {name: sequence.path for name, sequence in weapon.light_sequences.items()},
        ))
        errors = validate_runtime_payload(preflight)
        if errors:
            raise ValueError(f"Invalid weapon profile {source.name}:\n  " + "\n  ".join(errors))

        weapon_dir.mkdir(parents=True, exist_ok=True)

        clip_paths = self._copy_audio_assets(weapon, bank_name, name)
        light_paths = self._compile_light_assets(weapon, bank_name, name)
        runtime = normalize_runtime_payload(self._build_runtime_payload(weapon, clip_paths, light_paths))
        runtime_path = weapon_dir / "weapon.bin"
        runtime_path.write_bytes(encode_runtime(runtime))
        # Remove source-format output left by earlier exporter revisions.
        (weapon_dir / "weapon.json").unlink(missing_ok=True)
        for stale in (weapon_dir / "lights").glob("*.json"):
            stale.unlink()

        manifest_relative = runtime_path.relative_to(self.sd_root / "assets" / "weapons").as_posix()
        self._upsert_manifest(bank_name=bank_name, weapon_path=manifest_relative)
        return runtime_path

    def _copy_audio_assets(self, weapon: WeaponConfig, bank_name: str, weapon_name: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for clip_name, clip in weapon.clips.items():
            source = weapon.resolve_asset_path(clip.path).resolve()
            if not source.is_file():
                raise FileNotFoundError(f"Audio clip '{clip_name}' does not exist: {source}")
            relative_path = self.compiled_audio_path(bank_name, weapon_name, clip_name)
            destination = self.sd_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            export_audio_wav(source, destination)
            result[clip_name] = relative_path.as_posix()
        return result

    def _compile_light_assets(self, weapon: WeaponConfig, bank_name: str, weapon_name: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for sequence_name, sequence in weapon.light_sequences.items():
            source = weapon.resolve_asset_path(sequence.path).resolve()
            if not source.is_file():
                raise FileNotFoundError(f"Light sequence '{sequence_name}' does not exist: {source}")
            asset = self._load_sequence_asset(source, sequence_name)
            relative_path = self.compiled_light_path(bank_name, weapon_name, sequence_name)
            destination = self.sd_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(encode_sequence(asset))
            destination.with_suffix(".layout.bin").write_bytes(encode_layout(asset))
            result[sequence_name] = relative_path.as_posix()
        return result

    @staticmethod
    def _load_sequence_asset(source: Path, sequence_name: str):
        try:
            project = load_authored_project(source)
        except Exception:
            project = None
        if project is not None and sequence_name in project.animations:
            layout = load_project_layout(source, project)
            return compile_animation(layout=layout, animation=project.animations[sequence_name])
        try:
            return load_canvas_animation_sequence(source)
        except Exception:
            return load_light_sequence(source)

    @staticmethod
    def _build_runtime_payload(
        weapon: WeaponConfig,
        clip_paths: dict[str, str],
        light_paths: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "initial_state": weapon.initial_state,
            "variables": weapon.variables,
            "clips": {
                name: {"path": clip_paths[name], "preload": clip.preload}
                for name, clip in weapon.clips.items()
            },
            "clip_sets": {
                name: {"clips": list(item.clips), "mode": str(item.mode)}
                for name, item in weapon.clip_sets.items()
            },
            "audio_effects": {
                name: {
                    "clips": list(item.clips),
                    "mode": str(item.mode),
                    "interrupt": str(item.interrupt),
                    "loop": item.loop,
                    "gain": item.gain,
                }
                for name, item in weapon.audio_effects.items()
            },
            "light_sequences": {
                name: {"path": light_paths[name], "preload": item.preload}
                for name, item in weapon.light_sequences.items()
            },
            "states": [
                {
                    "id": state.id,
                    "label": state.label,
                    "on_entry": [_action_payload(action) for action in state.on_entry],
                    "on_exit": [_action_payload(action) for action in state.on_exit],
                }
                for state in weapon.states.values()
            ],
            "transitions": [
                {
                    "id": transition.id,
                    "source": transition.source,
                    "trigger": transition.trigger,
                    "target": transition.target,
                    **({"guard": _guard_payload(transition.guard)} if transition.guard is not None else {}),
                    "actions": [_action_payload(action) for action in transition.actions],
                    "internal": transition.internal,
                }
                for transition in weapon.transitions
            ],
        }

    def _upsert_manifest(self, *, bank_name: str, weapon_path: str) -> None:
        manifest_path = self.sd_root / MANIFEST_RELATIVE_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        if manifest_path.exists():
            banks = decode_manifest(manifest_path.read_bytes())
        else:
            banks = {}
        weapons = banks.setdefault(bank_name, [])
        if weapon_path not in weapons:
            weapons.append(weapon_path)
        manifest_path.write_bytes(encode_manifest(banks))
        # A legacy manifest must never be preferred by old embedded firmware.
        manifest_path.with_suffix(".json").unlink(missing_ok=True)

    def replace_bank(self, bank_name: str, weapon_paths: list[Path]) -> None:
        """Make a complete bank export authoritative, dropping stale manifest entries."""
        manifest_path = self.sd_root / MANIFEST_RELATIVE_PATH
        banks = decode_manifest(manifest_path.read_bytes()) if manifest_path.exists() else {}
        banks[bank_name] = [
            path.relative_to(self.sd_root / "assets" / "weapons").as_posix()
            for path in weapon_paths
        ]
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(encode_manifest(banks))
        manifest_path.with_suffix(".json").unlink(missing_ok=True)


def _default_profiles(profiles_root: Path) -> list[Path]:
    """Standalone weapon examples, excluding editor-only gun configuration documents."""
    import yaml

    return [
        path for path in sorted(profiles_root.glob("*.yaml"))
        if "weapon" in (yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export weapon FSM profiles and assets to an SD card")
    parser.add_argument("profiles", nargs="*", type=Path, help="Weapon YAML files (default: demo banks)")
    parser.add_argument("--sd-root", required=True, type=Path, help="Mounted SD card or staging directory")
    parser.add_argument("--bank", default="Default", help="Bank for explicit profiles")
    parser.add_argument("--all-banks", action="store_true", help="Export all migrated and curated profiles in their banks")
    args = parser.parse_args(argv)

    if args.all_banks:
        if args.profiles:
            parser.error("--all-banks cannot be combined with positional profiles")
        # Use the same validated, deduplicating compiler as the reproducible
        # standalone build. Do not maintain a second incompatible export path.
        from weapon_fsm_workspace.merged_sd import compile_bank_library

        banks = compile_bank_library(args.sd_root)
        for name, weapons in banks.items():
            print(f"{name}: {len(weapons)} compiled weapons")
        print(f"Total: {sum(map(len, banks.values()))} compiled weapons")
        return 0

    from weapon_fsm_workspace.paths import PROFILES_ROOT
    profiles_root = PROFILES_ROOT
    if args.profiles:
        batches = [(args.bank, args.profiles, False)]
    elif args.bank.lower() == "farts":
        batches = [("Farts", sorted((profiles_root / "farts").glob("*.yaml")), True)]
    else:
        batches = [(args.bank, _default_profiles(profiles_root), True)]
        if args.bank == "Default":
            # A complete Default export creates both usable demo banks.
            batches.append(("Farts", sorted((profiles_root / "farts").glob("*.yaml")), True))

    exporter = SdCardExporter(args.sd_root)
    failed: list[tuple[str, Path, Exception]] = []
    for bank, profiles, complete_bank in batches:
        success: list[Path] = []
        print(f"Exporting bank {bank} ({len(profiles)} profiles)")
        for profile in profiles:
            try:
                output = exporter.export_weapon(profile, bank_name=bank)
                success.append(output)
                print(f"  OK: {profile.name} -> {output}")
            except Exception as exc:
                failed.append((bank, profile, exc))
                print(f"  FAILED: {profile.name}: {exc}")

        if complete_bank and success:
            # Drop previously exported entries for profiles that no longer validate.
            exporter.replace_bank(bank, success)

    if failed:
        print("Export errors:")
        for bank, profile, exc in failed:
            print(f"  {bank}/{profile.name}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
