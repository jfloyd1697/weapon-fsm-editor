"""Migrate the original blaster-firmware/assets/weapons behavior.json bank library.

This runs on the PC, not on the microcontroller. The generated YAML is editable
in Weapon FSM Editor, and the normal SD exporter compiles it into WFSMBIN1.

Usage:
    python -m weapon_fsm_workspace.legacy_assets --firmware-assets path/to/assets
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
import wave
from pathlib import Path
from typing import Any

import yaml

BANK_NAMES = {"Fart": "Farts"}
REF_MISSING = {
    "assets/audio/charge_cannon/charge_start.wav": (330, 0.22),
    "assets/audio/charge_cannon/charge_loop.wav": (390, 0.5),
    "assets/audio/charge_cannon/charged.wav": (790, 0.18),
    "assets/audio/charge_cannon/fire_0.wav": (670, 0.23),
    "assets/audio/charge_cannon/fire_1.wav": (850, 0.23),
    "assets/audio/charge_cannon/cancel.wav": (230, 0.18),
    "assets/audio/charge_cannon/reload.wav": (460, 0.35),
}


def _generated_fallback(output: Path, frequency: int, duration: float) -> None:
    """Audible, explicitly documented placeholder for absent original source audio."""
    output.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44_100
    import struct
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        samples = bytearray()
        for i in range(round(duration * sample_rate)):
            t = i / sample_rate
            envelope = min(1.0, t * 70) * max(0.0, 1 - t / duration) ** 0.75
            value = round(8500 * envelope * math.sin(2 * math.pi * frequency * t))
            samples.extend(struct.pack("<h", value))
        stream.writeframes(samples)


class LegacyMigrator:
    def __init__(self, source_assets: Path, project_root: Path) -> None:
        self.source_assets = source_assets.resolve()
        self.project_root = project_root.resolve()
        self.assets = self.project_root / "assets"
        self.profiles = self.assets / "profiles/legacy"
        self.layout_path = self.assets / "lights/layouts/cpx_ring_61_outside_in.json"
        self.generated_patterns: set[str] = set()
        self._clip_sets: dict[tuple[str, ...], str] = {}
        self.missing_sources: set[str] = set()
        if not self.layout_path.is_file():
            raise FileNotFoundError(f"Outside-in 61-LED layout missing: {self.layout_path}")

    def migrate_all(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        originals = sorted((self.source_assets / "weapons").glob("*/*/behavior.json"))
        if not originals:
            raise FileNotFoundError(f"No legacy weapons at {self.source_assets / 'weapons'}")
        for file in originals:
            original_bank = file.parent.parent.name
            bank = BANK_NAMES.get(original_bank, original_bank)
            raw = json.loads(file.read_text(encoding="utf-8"))
            if raw.get("version") != 1:
                raise ValueError(f"Unexpected legacy behavior version in {file}")
            profile = self._migrate_one(raw, bank, file.parent.name)
            target = self.profiles / bank / f"{file.parent.name}.yaml"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(yaml.safe_dump(profile, sort_keys=False, allow_unicode=True), encoding="utf-8")
            counts[bank] = counts.get(bank, 0) + 1
        # Missing original sound effects are audible placeholders, not claimed originals.
        for missing in sorted(self.missing_sources):
            target = self.project_root / missing
            if missing in REF_MISSING:
                _generated_fallback(target, *REF_MISSING[missing])
            elif missing == "assets/audio/super_metroid_gun/reload.wav":
                original = self.assets / "audio/reload.wav"
                if not original.is_file():
                    raise FileNotFoundError(f"Missing substitute audio: {original}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
            else:
                raise FileNotFoundError(f"No available audio or explicit fallback for {missing}")
        (self.profiles / "MISSING_SOURCE_AUDIO.md").write_text(
            "# Original audio assets not supplied\n\n"
            "These legacy paths were referenced but absent in the uploaded firmware assets. "
            "Short synthesized PCM test tones were generated for charge_cannon, "
            "and super_metroid_gun/reload.wav uses the editor's generic reload clip. "
            "Replace these eight files with the intended original sounds when available; "
            "they are placeholders, not recovered recordings.\n\n"
            + "".join(f"- `{path}`\n" for path in sorted(self.missing_sources)), encoding="utf-8"
        )
        return counts

    def _copy_clip(self, relative: str) -> str:
        if not relative.startswith("assets/audio/") or ".." in Path(relative).parts:
            raise ValueError(f"Invalid legacy audio reference {relative!r}")
        source = self.source_assets.parent / relative
        destination = self.project_root / relative
        if source.is_file():
            if not destination.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        elif not destination.is_file():
            self.missing_sources.add(relative)
        return relative

    def _pattern_file(self, pattern: dict[str, Any]) -> str:
        key = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:12]
        filename = f"legacy_{key}.yaml"
        target = self.assets / "lights/legacy" / filename
        if key not in self.generated_patterns:
            target.parent.mkdir(parents=True, exist_ok=True)
            color = pattern.get("color", [0, 120, 255])
            if len(color) != 3 or any(not 0 <= x <= 255 for x in color):
                raise ValueError(f"Invalid legacy light color {color}")
            color_hex = "#" + "".join(f"{x:02x}" for x in color)
            peak = min(1.0, max(0.0, float(pattern.get("brightness", 255)) / 255.0))
            mode = pattern.get("mode", "solid")
            duration = int(pattern.get("intervalMs", 200))
            frames: list[dict[str, Any]] = []
            if mode == "solid":
                intensities = [(peak, 250)]
            elif mode == "pulse":
                intensities = [(peak * (0.12 + 0.88 * (1 - abs(2 * i / 15 - 1))), max(20, duration // 8))
                               for i in range(16)]
            elif mode == "flash":
                duration = max(20, int(pattern.get("durationMs", 80)))
                count = max(1, int(pattern.get("count", 1)))
                intensities = [(peak, duration), (0.0, 40)] * count
            else:
                raise ValueError(f"Unsupported legacy light mode {mode!r}")
            for intensity, ms in intensities:
                frames.append({
                    "duration_ms": ms,
                    "leds": {str(index): {"color": color_hex, "intensity": round(intensity, 4)}
                             for index in range(61)} if intensity > 0 else {},
                })
            # The relative path is from assets/lights/legacy/ to assets/lights/layouts/.
            target.write_text(yaml.safe_dump({
                "layout": {"path": "../layouts/cpx_ring_61_outside_in.json"},
                "frames": frames,
            }, sort_keys=False), encoding="utf-8")
            self.generated_patterns.add(key)
        return f"assets/lights/legacy/{filename}"

    def _migrate_one(self, raw: dict[str, Any], bank: str, name: str) -> dict[str, Any]:
        self._clip_sets.clear()
        clips: dict[str, dict[str, str]] = {}
        clip_sets: dict[str, dict[str, Any]] = {}
        lights: dict[str, dict[str, str]] = {}
        sequence_defs = raw.get("actionSequences", {})
        magazine = int(raw.get("magazineSize", 0))
        def clip_name(path: str) -> str:
            path = self._copy_clip(path)
            for existing, spec in clips.items():
                if spec["path"] == path:
                    return existing
            key = f"audio_{len(clips)}"
            clips[key] = {"path": path}
            return key

        def convert(actions: list[dict[str, Any]], *, depth: int = 0) -> list[dict[str, Any]]:
            if depth > 4:
                raise ValueError("Legacy action sequence recursion")
            result: list[dict[str, Any]] = []
            for action in actions:
                kind = action["type"]
                if kind == "run_sequence":
                    name_ref = action["name"]
                    if name_ref not in sequence_defs:
                        raise ValueError(f"Missing legacy action sequence {name_ref}")
                    result.extend(convert(sequence_defs[name_ref], depth=depth + 1))
                elif kind == "play_sound":
                    result.append({"type": "play_audio", "clip": clip_name(action["sound"]),
                                   "mode": "loop" if action.get("loop") else "once"})
                elif kind == "play_sound_random":
                    names = [clip_name(path) for path in action["sounds"]]
                    if not names:
                        raise ValueError("Empty randomized sound set")
                    if len(names) == 1:
                        result.append({"type": "play_audio", "clip": names[0]})
                    else:
                        result.append({"type": "play_random_audio", "clips": names})
                elif kind == "stop_sound":
                    result.append({"type": "stop_audio"})
                elif kind == "schedule_event":
                    result.append({"type": "schedule_event", "event": action["event"],
                                   "delay_ms": int(action["delayMs"])})
                elif kind in ("set_light", "flash_light"):
                    pattern = action["pattern"]
                    seq = f"light_{len(lights)}"
                    # C3-PO's reload/heal sound gets the actual red-heart layout, not a generic green pulse.
                    if bank == "Characters" and name == "c3p0_hurt" and pattern.get("mode") == "pulse" and pattern.get("color") == [0, 255, 80]:
                        relative = "assets/lights/heart_heal_red.yaml"
                    else:
                        relative = self._pattern_file(pattern)
                    lights[seq] = {"path": relative}
                    result.append({"type": "play_light", "sequence": seq,
                                   "mode": "once" if kind == "flash_light" or pattern.get("mode") == "flash" else "loop"})
                elif kind == "consume_ammo":
                    if magazine > 0:
                        result.append({"type": "adjust_ammo", "delta": -int(action.get("amount", 1))})
                        result.append({"type": "emit_event", "event": "ammo_empty"})
                elif kind == "flash_muzzle":
                    # The original runtime drove a hardware muzzle light. Preserve the
                    # visible effect on the configured 61-LED ring as a short flash.
                    colors = {
                        "Farts": [80, 255, 45],
                        "Characters": [255, 150, 25],
                        "SciFi": [150, 90, 255],
                        "Tools": [255, 80, 10],
                    }
                    seq = "muzzle_flash"
                    if seq not in lights:
                        path = self._pattern_file({
                            "mode": "flash", "color": colors.get(bank, [255, 195, 55]),
                            "brightness": 240, "durationMs": 95, "count": 1,
                        })
                        lights[seq] = {"path": path}
                    result.append({"type": "play_light", "sequence": seq, "mode": "once"})
                elif kind == "emit_shot":
                    # The fire-event is reflected in the audio and LED effects;
                    # no separate pulse actuator exists in the current platform.
                    pass
                else:
                    raise ValueError(f"Unmapped legacy action {kind}")
            return result

        states = []
        transitions = []
        for state_name, value in raw["states"].items():
            state = {"id": state_name, "label": state_name.replace("_", " ").title()}
            enter = convert(value.get("onEnter", []))
            exit_actions = convert(value.get("onExit", []))
            if state_name == "reloading":
                # The legacy runtime generated reload_complete implicitly, unlike the FSM core.
                if not any(x.get("type") == "schedule_event" and x.get("event") == "reload_complete" for x in enter):
                    enter.append({"type": "schedule_event", "event": "reload_complete", "delay_ms": 700})
            if enter:
                state["on_entry"] = enter
            if exit_actions:
                state["on_exit"] = exit_actions
            states.append(state)
            for index, transition in enumerate(value.get("transitions", [])):
                event = transition["event"]
                converted = {
                    "id": f"{state_name}_{index}_{event}",
                    "source": state_name,
                    "trigger": "reload_pressed" if event == "reload" else event,
                    "target": transition["target"],
                }
                actions = convert(transition.get("actions", []))
                if state_name == "reloading" and event == "reload_complete" and magazine > 0:
                    actions.append({"type": "set_ammo_full"})
                if actions:
                    converted["actions"] = actions
                if event == "ammo_empty" and magazine > 0:
                    converted["guard"] = {"var_lte": {"name": "ammo", "value": 0}}
                if state_name == converted["target"]:
                    converted["internal"] = True
                transitions.append(converted)
        variables = {"mag_capacity": magazine, "ammo": magazine} if magazine else {}
        result: dict[str, Any] = {
            "weapon": {
                "initial_state": raw["initialState"],
                "variables": variables,
                "clips": clips,
                "clip_sets": clip_sets,
                "light_sequences": lights,
                "states": states,
                "transitions": transitions,
            }
        }
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firmware-assets", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    options = parser.parse_args(argv)
    migration = LegacyMigrator(options.firmware_assets, options.project_root)
    counts = migration.migrate_all()
    for bank, count in sorted(counts.items()):
        print(f"{bank}: {count} profiles")
    print(f"Generated light patterns: {len(migration.generated_patterns)}")
    print(f"Missing original audio: {len(migration.missing_sources)} (documented placeholders)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
