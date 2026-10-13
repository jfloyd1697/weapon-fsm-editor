from pathlib import Path

from weapon_fsm_core.domain.model import WeaponConfig
from weapon_fsm_core.infrastructure.yaml.profile_schema import WeaponProfileFile
from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository


SAMPLE_WEAPON = """
weapon:
  initial_state: ready
  variables:
    ammo: 5
  clips:
    shot:
      path: assets/audio/shot.wav
  clip_sets:
    burst:
      clips: [shot]
      mode: cycle
  light_sequences:
    muzzle_flash:
      path: assets/lights/muzzle_flash.yaml
  states:
    - id: ready
      label: Ready
      on_entry:
        - type: play_sound
          clip: shot
    - id: firing
      label: Firing
  transitions:
    - id: fire
      source: ready
      trigger: trigger_pressed
      target: firing
      guard:
        ammo_gt: 0
      actions:
        - type: play_sound
          clip: shot
          interrupt: interrupt
"""


def test_weapon_profile_file_from_yaml_uses_mashumaro_round_trip():
    profile = WeaponProfileFile.from_dict(
        {
            "weapon": {
                "initial_state": "ready",
                "states": [{"id": "ready", "label": "Ready"}],
                "transitions": [],
            },
            "clips": {"shot": {"path": "assets/audio/shot.wav"}},
        }
    )

    dumped = profile.to_dict()

    assert dumped["weapon"]["initial_state"] == "ready"
    assert dumped["weapon"]["states"][0]["id"] == "ready"
    assert dumped["clips"]["shot"]["path"] == "assets/audio/shot.wav"


def test_weapon_config_from_dict_round_trip_uses_mashumaro():
    weapon = WeaponConfig.from_dict(
        {
            "initial_state": "ready",
            "variables": {"ammo": 3},
            "states": {"ready": {"id": "ready", "label": "Ready"}},
            "transitions": [
                {
                    "id": "fire",
                    "source": "ready",
                    "trigger": "trigger_pressed",
                    "target": "ready",
                    "actions": [{"type": "play_sound", "arguments": {"clip": "shot"}}],
                }
            ],
            "clips": {"shot": {"name": "shot", "path": "assets/audio/shot.wav"}},
            "source_path": "/tmp/weapon.yaml",
        }
    )

    dumped = weapon.to_dict()

    assert weapon.source_path == Path("/tmp/weapon.yaml")
    assert dumped["states"]["ready"]["label"] == "Ready"
    assert dumped["transitions"][0]["actions"][0]["arguments"]["clip"] == "shot"


def test_profile_repository_load_weapon_text_uses_mashumaro_models():
    repository = ProfileRepository()

    weapon = repository.load_weapon_text(SAMPLE_WEAPON, source_path="/tmp/demo/weapon.yaml")

    assert weapon.initial_state == "ready"
    assert weapon.variables["ammo"] == 5
    assert weapon.clips["shot"].path == "assets/audio/shot.wav"
    assert weapon.clip_sets["burst"].mode == "cycle"
    assert weapon.light_sequences["muzzle_flash"].path == "assets/lights/muzzle_flash.yaml"
    assert weapon.transitions[0].guard is not None
    assert weapon.transitions[0].guard.var_gt == {"name": "ammo", "value": 0}
    assert weapon.transitions[0].actions[0].arguments["clip"] == "shot"
