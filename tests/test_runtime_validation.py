"""Dependency-light tests for the embedded runtime export preflight."""

from weapon_fsm_workspace.runtime_validation import normalize_action_payload, validate_runtime_payload


def _valid_payload():
    return {
        "initial_state": "ready",
        "clips": {"shot": {"path": "assets/shot.wav"}},
        "light_sequences": {"flash": {"path": "assets/flash.bin"}},
        "states": [
            {"id": "ready", "on_entry": [
                {"type": "play_audio", "clip": "shot"},
                {"type": "start_light_sequence", "sequence": "flash"},
            ]},
        ],
        "transitions": [],
    }


def test_valid_runtime_payload():
    assert validate_runtime_payload(_valid_payload()) == []


def test_missing_clip_and_light_rejected():
    payload = _valid_payload()
    payload["states"][0]["on_entry"][0]["clip"] = "missing"
    payload["states"][0]["on_entry"][1]["sequence"] = "missing"
    issues = validate_runtime_payload(payload)
    assert any("unknown clip 'missing'" in issue for issue in issues)
    assert any("unknown light sequence 'missing'" in issue for issue in issues)


def test_random_audio_checks_all_references():
    payload = _valid_payload()
    payload["states"][0]["on_entry"] = [
        {"type": "play_random_audio", "clips": ["shot", "missing"]}
    ]
    assert any("unknown clip 'missing'" in issue for issue in validate_runtime_payload(payload))


def test_gun_only_and_unsupported_action_are_rejected():
    payload = _valid_payload()
    payload["states"] = []
    assert any("states must not be empty" in issue for issue in validate_runtime_payload(payload))
    payload = _valid_payload()
    payload["states"][0]["on_entry"] = [{"type": "unsupported"}]
    assert any("unknown action type" in issue for issue in validate_runtime_payload(payload))


def test_bad_transition_rejected():
    payload = _valid_payload()
    payload["transitions"].append({
        "source": "ready", "target": "missing", "trigger": "fire", "actions": []
    })
    assert any("unknown target" in issue for issue in validate_runtime_payload(payload))


def test_legacy_play_sound_is_compiled_to_supported_action():
    assert normalize_action_payload("play_sound", {"clip": "shot"}) == {
        "type": "play_audio", "clip": "shot"
    }


def test_real_demo_profile_references_are_checked():
    from pathlib import Path
    import yaml

    demos = Path(__file__).resolve().parents[1] / "src" / "weapon_fsm_workspace" / "demos"
    for filename in ("aiai_health.yaml", "character_sounds.yaml", "metroid_prime.yaml"):
        authored = yaml.safe_load((demos / filename).read_text(encoding="utf-8"))
        weapon = authored["weapon"]
        clips = weapon.get("clips", authored.get("clips", {}))
        sequences = weapon.get("light_sequences", authored.get("light_sequences", {}))
        payload = {
            "initial_state": weapon.get("initial_state", "ready"),
            "clips": clips,
            "clip_sets": weapon.get("clip_sets", authored.get("clip_sets", {})),
            "audio_effects": weapon.get("audio_effects", authored.get("audio_effects", {})),
            "light_sequences": sequences,
            "states": weapon.get("states", []),
            "transitions": weapon.get("transitions", []),
        }
        for state in payload["states"]:
            for field in ("on_entry", "on_exit"):
                state[field] = [normalize_action_payload(a["type"], {k: v for k, v in a.items() if k != "type"})
                                for a in state.get(field, [])]
        for transition in payload["transitions"]:
            transition["actions"] = [normalize_action_payload(a["type"], {k: v for k, v in a.items() if k != "type"})
                                     for a in transition.get("actions", [])]
        assert validate_runtime_payload(payload) == [], filename
