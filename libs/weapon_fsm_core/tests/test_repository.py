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
    assert weapon.source_path == weapon_path.parent


def test_assets_root_is_not_nested_when_an_assets_child_exists(tmp_path: Path) -> None:
    project = tmp_path / "editor"
    profiles = project / "assets/profiles/legacy/Default"
    audio = project / "assets/audio/slave1"
    lighting = project / "assets/lights/legacy"
    profiles.mkdir(parents=True)
    audio.mkdir(parents=True)
    lighting.mkdir(parents=True)
    # A stray nested assets directory must not change asset-root selection.
    (project / "assets/assets/audio").mkdir(parents=True)
    (audio / "shot.wav").write_bytes(b"wav")
    (lighting / "flash.yaml").write_text("frames: []", encoding="utf-8")
    profile = profiles / "slave_one.yaml"
    profile.write_text(
        "clips:\n  shot: assets/audio/slave1/shot.wav\n"
        "light_sequences:\n  flash: assets/lights/legacy/flash.yaml\n"
        "weapon:\n  initial_state: idle\n  states:\n    - id: idle\n  transitions: []\n",
        encoding="utf-8",
    )

    weapon = ProfileRepository().load_weapon(profile)

    assert weapon.source_path == project
    assert weapon.resolve_asset_path(weapon.clips["shot"].path) == audio / "shot.wav"
    assert weapon.resolve_asset_path(weapon.light_sequences["flash"].path) == lighting / "flash.yaml"


def test_default_gun_supports_trigger_held() -> None:
    project_root = Path(__file__).resolve().parents[3]
    gun = ProfileRepository().load_gun(project_root / "assets/profiles/default_gun.yaml")

    assert "trigger_held" in gun.events
