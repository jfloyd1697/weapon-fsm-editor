from pathlib import Path

from weapon_fsm_core.domain.commands import GunRuntimeCommand
from weapon_fsm_core.domain.model import GunConfig
from weapon_fsm_core.domain.runtime import WeaponRuntime
from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository


def test_runtime_emits_resolved_audio_and_light_payloads(tmp_path: Path) -> None:
    audio_dir = tmp_path / "assets" / "audio"
    light_dir = tmp_path / "assets" / "lights"
    audio_dir.mkdir(parents=True)
    light_dir.mkdir(parents=True)
    (audio_dir / "blast.wav").write_text("wav", encoding="utf-8")
    (light_dir / "flash.yaml").write_text("lights", encoding="utf-8")

    weapon_path = tmp_path / "weapon.yaml"
    weapon_path.write_text(
        """
weapon:
  initial_state: ready
  states:
    - id: ready
      label: Ready
      on_entry:
        - type: play_audio
          clip: blast
        - type: play_light
          sequence: flash
  transitions: []
clips:
  blast:
    path: assets/audio/blast.wav
light_sequences:
  flash:
    path: assets/lights/flash.yaml
""",
        encoding="utf-8",
    )

    weapon = ProfileRepository().load_weapon(weapon_path)
    runtime = WeaponRuntime(GunConfig(events=()), weapon)

    assert runtime.current_state == "ready"
    commands = runtime._run_actions(weapon.states["ready"].on_entry)[2]
    audio_cmd = next(cmd for cmd in commands if isinstance(cmd, GunRuntimeCommand) and cmd.type == "play_audio")
    light_cmd = next(cmd for cmd in commands if isinstance(cmd, GunRuntimeCommand) and cmd.type == "play_light")

    assert audio_cmd.payload["clip"] == "blast"
    assert audio_cmd.payload["path"] == str((audio_dir / "blast.wav").resolve())
    assert audio_cmd.payload["mode"] == "one_shot"
    assert light_cmd.payload["sequence"] == "flash"
    assert light_cmd.payload["path"] == str((light_dir / "flash.yaml").resolve())


def test_play_sound_random_uses_named_clip_set(tmp_path: Path) -> None:
    audio_dir = tmp_path / "assets" / "audio"
    audio_dir.mkdir(parents=True)
    (audio_dir / "a.wav").write_text("wav", encoding="utf-8")
    (audio_dir / "b.wav").write_text("wav", encoding="utf-8")

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
          clip_set: shots
  transitions: []
clips:
  shot_a:
    path: assets/audio/a.wav
  shot_b:
    path: assets/audio/b.wav
clip_sets:
  shots:
    mode: sequence
    clips:
      - shot_a
      - shot_b
""",
        encoding="utf-8",
    )

    weapon = ProfileRepository().load_weapon(weapon_path)
    runtime = WeaponRuntime(GunConfig(events=()), weapon)

    first = runtime._run_actions(weapon.states["ready"].on_entry)[2]
    second = runtime._run_actions(weapon.states["ready"].on_entry)[2]
    first_audio = next(cmd for cmd in first if isinstance(cmd, GunRuntimeCommand) and cmd.type == "play_audio")
    second_audio = next(cmd for cmd in second if isinstance(cmd, GunRuntimeCommand) and cmd.type == "play_audio")

    assert first_audio.payload["clip"] == "shot_b"
    assert second_audio.payload["clip"] == "shot_a"
