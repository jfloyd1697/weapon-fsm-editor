from __future__ import annotations

from pathlib import Path

from libs.asset_integration.compile import compile_action
from libs.asset_integration.compile.parser import parse_weapon_yaml
from libs.asset_integration.compile.validator import validate_weapon
from libs.asset_integration.runtime.commands import PlayAudioCommand


EXAMPLE_YAML = """
weapon:
  initial_state: ready

clips:
  charge_loop:
    path: assets/audio/charge_loop.wav

light_sequences:
  glow:
    path: assets/lights/glow.yaml

states:
  - id: ready
    label: Ready
    on_entry:
      - type: play_audio
        clip: charge_loop
        mode: loop
      - type: play_light
        sequence: glow

transitions: []
"""


def test_parse_and_compile(tmp_path: Path) -> None:
    weapon_file = tmp_path / "weapon.yaml"
    (tmp_path / "assets/audio").mkdir(parents=True)
    (tmp_path / "assets/lights").mkdir(parents=True)
    (tmp_path / "assets/audio/charge_loop.wav").write_bytes(b"RIFF")
    (tmp_path / "assets/lights/glow.yaml").write_text("steps: []\n", encoding="utf-8")
    weapon_file.write_text(EXAMPLE_YAML, encoding="utf-8")

    weapon = parse_weapon_yaml(EXAMPLE_YAML)
    issues = validate_weapon(weapon, weapon_file)
    assert issues == []

    command = compile_action(weapon.states[0].on_entry[0], weapon, weapon_file)
    assert isinstance(command, PlayAudioCommand)
    assert command.clip_name == "charge_loop"
    assert command.mode == "loop"
