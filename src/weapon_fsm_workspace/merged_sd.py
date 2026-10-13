"""Compile all supplied weapon banks to SD assets without any GUI dependencies.

This uses the same binary encoders, audio normalizer, and preflight validation as
``weapon-fsm-export-sd``. The input profiles are editable YAML; only binaries
and normalized audio are written to the SD directory.

Usage:
    PYTHONPATH=src python tools/build_merged_sd.py --sd-root /path/to/card
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

# Permit running this script directly from a checked-out workspace.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from weapon_fsm_workspace.light_project_compiler import compile_animation_project
from weapon_fsm_workspace.audio_export import export_audio_wav
from weapon_fsm_workspace.compiled_assets import (
    encode_layout,
    encode_manifest,
    encode_sequence,
)
from weapon_fsm_workspace.runtime_binary import encode_runtime
from weapon_fsm_workspace.runtime_validation import normalize_runtime_payload, validate_runtime_payload

DEMOS = ROOT / "src/weapon_fsm_workspace/demos"
MANIFEST = Path("assets/weapons/weapons_manifest.bin")
EXTRAS = {
    "Characters": ("yoda_hurt", "darth_maul_hurt"),
    "Default": ("aiai_fallout", "aiai_health", "C3_hurt", "metroid_prime"),
}


def profiles_by_bank(demos: Path = DEMOS) -> dict[str, list[Path]]:
    result = {
        path.name: sorted(path.glob("*.yaml"))
        for path in (demos / "legacy").iterdir()
        if path.is_dir()
    }
    for bank, names in EXTRAS.items():
        result.setdefault(bank, []).extend(demos / f"{name}.yaml" for name in names)
    return result


def _asset_path(demos: Path, reference: str) -> Path:
    path = (demos / reference).resolve()
    if not path.is_relative_to(demos.resolve()) or not path.is_file():
        raise FileNotFoundError(f"Missing or unsafe source asset: {reference}")
    return path


def _load_sequence(source: Path, sequence_name: str):
    """Read the existing frame-authored light YAML, including its layout file."""
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not (isinstance(raw.get("frames"), list) or "animations" in raw):
        raise ValueError(f"Expected a frame-authored sequence or animation project: {source}")
    layout_path = (source.parent / raw["layout"]["path"]).resolve()
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    if layout.get("coordinate_space") != "normalized_2d":
        raise ValueError(f"Unsupported LED coordinate system: {layout_path}")
    leds = tuple(SimpleNamespace(
        id=str(led.get("id", led["index"])),
        index=int(led["index"]),
        x=float(led["u"]),
        y=float(led["v"]),
        radius=float(led["led_radius"]),
    ) for led in layout["leds"])
    if sorted(led.index for led in leds) != list(range(len(leds))):
        raise ValueError(f"LED indices must be contiguous: {layout_path}")
    if "animations" in raw:
        if sequence_name not in raw["animations"]:
            raise ValueError(f"Unknown animation {sequence_name!r} in {source}")
        return compile_animation_project(source, sequence_name, leds)
    frames = []
    for frame in raw["frames"]:
        active = {
            str(index): (value["color"], float(value.get("intensity", 1.0)))
            for index, value in frame["leds"].items()
        }
        frames.append(SimpleNamespace(duration_ms=int(frame["duration_ms"]), leds=active))
    if not frames:
        raise ValueError(f"Sequence has no frames: {source}")
    return SimpleNamespace(leds=leds, frames=tuple(frames), width=1.0, height=1.0)


def _weapon_payload(weapon: dict[str, Any], audio_paths: dict[str, str], light_paths: dict[str, str]):
    return {
        "initial_state": weapon["initial_state"],
        "variables": weapon.get("variables", {}),
        "clips": {name: {"path": audio_paths[name], "preload": clip.get("preload", False) if isinstance(clip, dict) else False}
                  for name, clip in weapon.get("clips", {}).items()},
        "clip_sets": weapon.get("clip_sets", {}),
        "audio_effects": weapon.get("audio_effects", {}),
        "light_sequences": {name: {"path": light_paths[name], "preload": seq.get("preload", False) if isinstance(seq, dict) else False}
                            for name, seq in weapon.get("light_sequences", {}).items()},
        "states": weapon.get("states", []),
        "transitions": weapon.get("transitions", []),
    }


def compile_bank_library(sd_root: Path, demos: Path = DEMOS) -> dict[str, list[str]]:
    sd_root.mkdir(parents=True, exist_ok=True)
    banks: dict[str, list[str]] = {}
    audio_cache: dict[str, Path] = {}
    sequence_cache: dict[tuple[Path, str], tuple[bytes, bytes]] = {}
    errors: list[str] = []
    for bank, profiles in sorted(profiles_by_bank(demos).items()):
        entries = []
        for profile in profiles:
            try:
                source = yaml.safe_load(profile.read_text(encoding="utf-8"))
                if not isinstance(source, dict) or not isinstance(source.get("weapon"), dict):
                    raise ValueError("Missing weapon section")
                weapon = dict(source["weapon"])
                for section in ("clips", "clip_sets", "light_sequences", "audio_effects"):
                    if section not in weapon and section in source:
                        weapon[section] = source[section]
                if not weapon.get("states"):
                    raise ValueError("No FSM states")
                relative_dir = Path("assets/weapons") / bank / profile.stem
                destination = sd_root / relative_dir
                audio_paths = {}
                for name, clip in weapon.get("clips", {}).items():
                    clip_ref = clip if isinstance(clip, str) else clip["path"]
                    audio_src = _asset_path(demos, clip_ref)
                    # Global content-addressed audio deduplication, across all banks.
                    # Identical source WAV data needs to be normalized only once.
                    digest = hashlib.sha256(audio_src.read_bytes()).hexdigest()[:24]
                    audio_dst = sd_root / "assets/audio/shared" / (digest + ".wav")
                    audio_paths[name] = audio_dst.relative_to(sd_root).as_posix()
                    if digest not in audio_cache:
                        if not audio_dst.is_file():
                            audio_dst.parent.mkdir(parents=True, exist_ok=True)
                            export_audio_wav(audio_src, audio_dst)
                        audio_cache[digest] = audio_dst
                light_paths = {}
                for name, seq in weapon.get("light_sequences", {}).items():
                    seq_ref = seq if isinstance(seq, str) else seq["path"]
                    light_src = _asset_path(demos, seq_ref)
                    key = (light_src, name if "animations" in light_src.read_text(encoding="utf-8")[:600] else "")
                    if key not in sequence_cache:
                        asset = _load_sequence(light_src, name)
                        if len(asset.leds) != 61:
                            raise ValueError(f"Expected 61 LEDs in {light_src}")
                        sequence_cache[key] = (encode_sequence(asset), encode_layout(asset))
                    compiled, layout = sequence_cache[key]
                    digest = hashlib.sha256(compiled + layout).hexdigest()[:24]
                    light_dst = sd_root / "assets/lights/shared" / (digest + ".bin")
                    if not light_dst.is_file():
                        light_dst.parent.mkdir(parents=True, exist_ok=True)
                        light_dst.write_bytes(compiled)
                        light_dst.with_suffix(".layout.bin").write_bytes(layout)
                    light_paths[name] = light_dst.relative_to(sd_root).as_posix()
                runtime = normalize_runtime_payload(_weapon_payload(weapon, audio_paths, light_paths))
                violations = validate_runtime_payload(runtime)
                if violations:
                    raise ValueError("; ".join(violations))
                weapon_dst = destination / "weapon.bin"
                weapon_dst.parent.mkdir(parents=True, exist_ok=True)
                weapon_dst.write_bytes(encode_runtime(runtime))
                entries.append(weapon_dst.relative_to(sd_root / "assets/weapons").as_posix())
            except Exception as error:
                errors.append(f"{bank}/{profile.name}: {error}")
        if entries:
            banks[bank] = entries
    if errors:
        raise RuntimeError("Failed to export profiles:\n" + "\n".join(errors))
    manifest = sd_root / MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes(encode_manifest(banks))
    return banks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sd-root", type=Path, required=True)
    args = parser.parse_args()
    banks = compile_bank_library(args.sd_root)
    for bank, paths in banks.items():
        print(f"{bank}: {len(paths)} compiled weapons")
    print(f"Total: {sum(map(len, banks.values()))} compiled weapons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
