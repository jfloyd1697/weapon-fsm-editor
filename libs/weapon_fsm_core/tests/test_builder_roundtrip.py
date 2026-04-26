from pathlib import Path

from weapon_fsm_audio import AudioConfigBuilder
from weapon_fsm_core.application.builders import ActionFactory, WeaponProfileBuilder
from weapon_fsm_core.infrastructure.yaml.profile_mapper import ProfileYamlMapper
from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository


def test_builder_write_and_load_round_trip(tmp_path: Path) -> None:
    builder = WeaponProfileBuilder()
    audio = AudioConfigBuilder(builder)

    builder.set_events(["trigger_pressed", "fire_done"])
    builder.set_initial_state("ready")
    builder.ensure_state("ready", "Ready")
    builder.ensure_state("firing", "Firing")

    audio.set_clip("shot", "assets/audio/shot.wav")
    audio.set_effect("fire_effect", clip="shot", mode="one_shot")

    builder.add_transition("fire", "ready", "trigger_pressed", "firing")
    audio.bind_transition_effect("fire", "fire_effect")
    builder.append_transition_action("fire", ActionFactory.schedule_event("fire_done", 100))
    builder.add_transition("done", "firing", "fire_done", "ready")

    gun = builder.build_gun()
    weapon = builder.build_weapon()

    gun_path = tmp_path / "gun.yaml"
    weapon_path = tmp_path / "weapon.yaml"
    ProfileYamlMapper.write_gun(gun, gun_path)
    ProfileYamlMapper.write_weapon(weapon, weapon_path)

    repo = ProfileRepository()
    loaded_gun = repo.load_gun(gun_path)
    loaded_weapon = repo.load_weapon(weapon_path)

    assert loaded_gun.events == ("trigger_pressed", "fire_done")
    assert loaded_weapon.initial_state == "ready"
    assert "ready" in loaded_weapon.states
    assert loaded_weapon.clips["shot"].path == "assets/audio/shot.wav"
    assert loaded_weapon.audio_effects["fire_effect"].clips == ("shot",)
    assert loaded_weapon.transitions[0].actions[0].type == "play_audio_effect"
    assert loaded_weapon.transitions[0].actions[0].argument("effect") == "fire_effect"
