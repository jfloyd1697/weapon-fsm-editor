from weapon_fsm_core.infrastructure.yaml.profile_builder import ActionBuilder, WeaponProfileBuilder


def test_profile_builder_emits_trimmed_audio_yaml():
    builder = WeaponProfileBuilder()
    builder.set_initial_state("ready")
    builder.ensure_state("ready", "Ready")
    builder.set_transition(
        "fire",
        source="ready",
        target="ready",
        trigger="trigger_pressed",
    )
    builder.set_audio_clip("blast_a", "assets/audio/blast_a.wav")
    builder.set_audio_effect("fire_basic", clip="blast_a")
    builder.append_transition_action("fire", ActionBuilder.play_audio_effect("fire_basic"))

    text = builder.to_yaml()

    assert "audio:" in text
    assert "effects:" in text
    assert "gain:" not in text
    assert "loop:" not in text
    assert "arguments:" not in text
    assert "interrupt:" not in text
    assert "mode:" not in text
    assert "effect: fire_basic" in text


def test_profile_builder_can_round_trip_compacted_yaml():
    source = """
weapon:
  initial_state: ready
  states:
    - id: ready
      label: Ready
  transitions:
    - id: fire
      source: ready
      target: ready
      trigger: trigger_pressed
      actions:
        - type: play_audio_effect
          effect: fire_basic
audio:
  clips:
    blast_a:
      path: assets/audio/blast_a.wav
  effects:
    fire_basic:
      clips:
        - blast_a
"""
    builder = WeaponProfileBuilder.from_yaml(source)
    builder.set_audio_effect("charge_loop", clip="blast_a", mode="loop")

    text = builder.to_yaml()

    assert "charge_loop:" in text
    assert "mode: loop" in text
