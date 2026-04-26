from weapon_fsm_core.application.builders import WeaponProfileBuilder
from weapon_fsm_core import ActionFactory
from weapon_fsm_core.infrastructure.yaml.profile_mapper import ProfileYamlMapper


def test_profile_builder_is_format_neutral_and_serializes_through_mapper():
    builder = WeaponProfileBuilder()
    builder.set_events(["trigger_pressed", "reload_pressed"])
    builder.ensure_state("ready", label="Ready")
    builder.ensure_state("reloading", label="Reloading")
    builder.add_transition(
        "reload",
        source="ready",
        trigger="reload_pressed",
        target="reloading",
    )
    builder.set_clip("reload_click", "assets/audio/reload_click.wav")
    builder.append_transition_action(
        "reload",
        ActionFactory.create("play_audio", clip="reload_click"),
    )

    weapon = builder.build_weapon()
    gun = builder.build_gun()

    assert gun.events == ("trigger_pressed", "reload_pressed")
    assert weapon.clips["reload_click"].path == "assets/audio/reload_click.wav"
    assert weapon.transitions[0].actions[0].arguments["clip"] == "reload_click"

    yaml_text = ProfileYamlMapper.weapon_to_yaml(weapon)

    assert "weapon:" in yaml_text
    assert "clips:" in yaml_text
    assert "type: play_audio" in yaml_text
    assert "clip: reload_click" in yaml_text


def test_builder_can_replace_audio_effect_actions_without_touching_yaml_layer():
    builder = WeaponProfileBuilder()
    builder.ensure_state("ready")
    builder.add_transition("fire", source="ready", trigger="trigger_pressed", target="ready")
    builder.append_transition_action("fire", ActionFactory.play_audio_effect("old_effect"))
    builder.remove_transition_actions_by_type("fire", "play_audio_effect")
    builder.append_transition_action("fire", ActionFactory.play_audio_effect("new_effect"))

    transition = builder.require_transition("fire")

    assert len(transition.actions) == 1
    assert transition.actions[0].type == "play_audio_effect"
    assert transition.actions[0].arguments == {"effect": "new_effect"}
