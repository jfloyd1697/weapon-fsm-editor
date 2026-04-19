from pathlib import Path

from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository


WEAPON_YAML = """
weapon:
  initial_state: ready
  variables:
    charge_ticks: 0
  states:
    - id: ready
      label: Ready
      on_entry:
        - type: play_audio
          clip: ready_hum
    - id: firing
      label: Firing
  transitions:
    - id: fire
      source: ready
      trigger: trigger_pressed
      target: firing
      actions:
        - type: play_light
          sequence: muzzle_flash
clips:
  ready_hum:
    path: assets/audio/ready_hum.wav
light_sequences:
  muzzle_flash:
    path: assets/lights/muzzle_flash.yaml
"""


def test_repository_loads_assets_and_source_path(tmp_path: Path) -> None:
    weapon_path = tmp_path / "weapon.yaml"
    weapon_path.write_text(WEAPON_YAML, encoding="utf-8")

    repo = ProfileRepository()
    weapon = repo.load_weapon(weapon_path)

    assert weapon.initial_state == "ready"
    assert "ready" in weapon.states
    assert weapon.clips["ready_hum"].path == "assets/audio/ready_hum.wav"
    assert weapon.light_sequences["muzzle_flash"].path == "assets/lights/muzzle_flash.yaml"
    assert weapon.source_path == weapon_path
