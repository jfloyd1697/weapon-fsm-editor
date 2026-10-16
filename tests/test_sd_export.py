from pathlib import Path
import json
import shutil
import wave

import pytest

from weapon_fsm_workspace.sd_export import SdCardExporter


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_export_weapon_creates_runtime_manifest_and_assets(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "assets/audio").mkdir(parents=True)
    (project / "assets/lights").mkdir(parents=True)
    with wave.open(str(project / "assets/audio/fire.wav"), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22050)
        output.writeframes(b"\x00\x00" * 2205)
    (project / "assets/lights/layout.json").write_text(
        json.dumps({
            "coordinate_space": "normalized_2d",
            "leds": [{"index": 0, "u": 0.5, "v": 0.5}],
        }),
        encoding="utf-8",
    )
    (project / "assets/lights/fire.yaml").write_text(
        "layout:\n  path: layout.json\nframes:\n  - duration_ms: 10\n    leds:\n      '0': {color: '#ffffff', intensity: 1.0}\n",
        encoding="utf-8",
    )
    profile = project / "weapon.yaml"
    profile.write_text(
        "clips:\n  fire: assets/audio/fire.wav\nlight_sequences:\n  flash: assets/lights/fire.yaml\nweapon:\n  initial_state: ready\n  states:\n    - id: ready\n      label: Ready\n      on_entry:\n        - type: play_audio\n          clip: fire\n        - type: play_light\n          sequence: flash\n  transitions: []\n",
        encoding="utf-8",
    )

    sd_root = tmp_path / "sd"
    runtime_path = SdCardExporter(sd_root).export_weapon(profile, bank_name="Test")

    runtime = runtime_path.read_bytes()
    assert runtime.startswith(b"WFSMBIN1")
    assert runtime_path.name == "weapon.bin"
    with wave.open(str(runtime_path.parent / "audio/fire.wav"), "rb") as output:
        assert output.getframerate() == 44100
        assert output.getnchannels() == 1
        assert output.getsampwidth() == 2
    assert (runtime_path.parent / "lights/flash.bin").is_file()
    assert (runtime_path.parent / "lights/flash.layout.bin").is_file()
    # Firmware treats compiled audio and lighting paths as SD-root-relative.
    audio_ref = SdCardExporter.compiled_audio_path("Test", "weapon", "fire")
    light_ref = SdCardExporter.compiled_light_path("Test", "weapon", "flash")
    assert audio_ref.as_posix().encode() in runtime
    assert light_ref.as_posix().encode() in runtime
    assert (sd_root / audio_ref).is_file()
    assert (sd_root / light_ref).is_file()
    assert b"assets/assets/" not in runtime

    from weapon_fsm_workspace.compiled_assets import decode_manifest

    manifest_path = sd_root / "assets/weapons/weapons_manifest.bin"
    assert decode_manifest(manifest_path.read_bytes()) == {"Test": ["Test/weapon/weapon.bin"]}
    assert not manifest_path.with_suffix(".json").exists()
