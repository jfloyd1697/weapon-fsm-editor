"""Regenerate fixture files after changing a binary format.

PYTHONPATH=src python tests/generate_firmware_fixtures.py /path/to/firmware/tests/data/compiled_assets
"""
from __future__ import annotations

import argparse
from pathlib import Path

from weapon_fsm_workspace.compiled_assets import encode_manifest, encode_sequence, encode_layout
from weapon_fsm_workspace.runtime_binary import encode_runtime

from test_compiled_assets import Asset, Frame, Led, sample


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    assets = args.destination / "assets"
    weapon = assets / "weapons" / "Default" / "test"
    lights = assets / "lights"
    audio = assets / "audio"
    for directory in (weapon, lights, audio, assets / "weapons"):
        directory.mkdir(parents=True, exist_ok=True)
    (assets / "weapons" / "weapons_manifest.bin").write_bytes(encode_manifest({
        "Default": ["Default/test/weapon.bin"],
    }))
    (lights / "flash.bin").write_bytes(encode_sequence(sample()))
    # Representative animation larger than the STM32F411's usable free heap.
    big_asset = Asset(1.0, 1.0, tuple(Led(str(i), i) for i in range(61)),
                      tuple(Frame(33, {str(i): ("#0080ff", 0.8) for i in range(61)})
                            for _ in range(500)))
    (lights / "large.bin").write_bytes(encode_sequence(big_asset))
    (lights / "flash.layout.bin").write_bytes(encode_layout(sample()))
    (audio / "fire.wav").write_bytes(b"RIFF")
    (weapon / "weapon.bin").write_bytes(encode_runtime({
        "initial_state": "ready",
        "clips": {"shot": {"path": "assets/audio/fire.wav", "preload": False}},
        "light_sequences": {"flash": {"path": "assets/lights/flash.bin", "preload": False}},
        "states": [{"id": "ready", "label": "Ready", "on_entry": [], "on_exit": []}],
        "transitions": [],
    }))


if __name__ == "__main__":
    main()
