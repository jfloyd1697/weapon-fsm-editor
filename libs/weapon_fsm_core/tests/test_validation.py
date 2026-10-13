from pathlib import Path

from weapon_fsm_core.domain.model import GunConfig
from weapon_fsm_core.domain.validation import ProfileValidator
from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository


def test_validator_reports_unknown_clip_reference() -> None:
    gun = GunConfig(events=("trigger_pressed",))
    weapon = ProfileRepository().load_weapon_text(
        """
weapon:
  initial_state: ready
  states:
    - id: ready
      label: Ready
      on_entry:
        - type: play_audio
          clip: missing_clip
  transitions: []
clips: {}
light_sequences: {}
"""
    )

    issues = ProfileValidator().validate(gun, weapon)
    assert any("Unknown clip 'missing_clip'" in issue.message for issue in issues)


def test_validator_reports_missing_asset_file(tmp_path: Path) -> None:
    gun = GunConfig(events=("trigger_pressed",))
    weapon_path = tmp_path / "weapon.yaml"
    weapon_path.write_text(
        """
weapon:
  initial_state: ready
  states:
    - id: ready
      label: Ready
  transitions: []
clips:
  ready_hum:
    path: assets/audio/ready_hum.wav
light_sequences: {}
""",
        encoding="utf-8",
    )

    weapon = ProfileRepository().load_weapon(weapon_path)
    issues = ProfileValidator().validate(gun, weapon)

    assert any("points to missing file" in issue.message for issue in issues)



def test_validation_reports_unknown_clip_set_members(tmp_path):
    weapon_path = tmp_path / "weapon.yaml"
    weapon_path.write_text(
        """
weapon:
  initial_state: ready
  states:
    - id: ready
      label: Ready
      on_entry:
        - type: play_sound_random
          clip_set: variants
  transitions: []
clips:
  blast:
    path: blast.wav
clip_sets:
  variants:
    clips:
      - blast
      - missing_clip
""",
        encoding="utf-8",
    )

    from weapon_fsm_core.domain.model import GunConfig
    from weapon_fsm_core.domain.validation import ProfileValidator
    from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository

    weapon = ProfileRepository().load_weapon(weapon_path)
    issues = ProfileValidator().validate(GunConfig(events=()), weapon)

    assert any(issue.path == "clip_sets.variants.clips" and "missing_clip" in issue.message for issue in issues)
