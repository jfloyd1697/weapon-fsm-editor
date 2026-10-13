"""Regression tests for selecting a new weapon or LEGO character."""

from __future__ import annotations

import math
from pathlib import Path

import yaml

from weapon_fsm_workspace.merged_sd import DEMOS, _load_sequence, profiles_by_bank
from weapon_fsm_workspace.runtime_validation import validate_runtime_payload


def load(profile: Path) -> dict:
    raw = yaml.safe_load(profile.read_text(encoding='utf-8'))
    weapon = raw['weapon']
    for field in ('clips', 'light_sequences', 'clip_sets', 'audio_effects'):
        if field not in weapon and field in raw:
            weapon[field] = raw[field]
    return weapon


def actions(weapon: dict, state_name: str) -> list[dict]:
    return next(state for state in weapon['states'] if state['id'] == state_name)['on_entry']


def sequence_for(weapon: dict, name: str):
    value = weapon['light_sequences'][name]
    path = value if isinstance(value, str) else value['path']
    source = DEMOS / path
    return yaml.safe_load(source.read_text(encoding='utf-8')), _load_sequence(source, name)


def test_prime_equips_with_outward_then_inward_pulse():
    weapon = load(DEMOS / 'metroid_prime.yaml')
    equip = actions(weapon, 'equipping')
    assert any(a.get('type') == 'play_audio' and a.get('clip') == 'equip' for a in equip)
    assert any(a.get('type') == 'play_light' and a.get('sequence') == 'prime_equip_radial' for a in equip)
    assert validate_runtime_payload(weapon) == []
    raw, compiled = sequence_for(weapon, 'prime_equip_radial')
    assert raw['layout']['path'] == 'layouts/cpx_ring_61_outside_in.json'
    assert len(compiled.leds) == 61
    assert len(compiled.frames) == 17
    assert sum(f['duration_ms'] for f in raw['frames']) == 476
    # LED 60 is center; LEDs 0–23 are outside. Pulse starts and ends in center.
    center = [f['leds'].get('60', {}).get('intensity', 0) for f in raw['frames']]
    outside = [max((f['leds'].get(str(i), {}).get('intensity', 0) for i in range(24)), default=0)
               for f in raw['frames']]
    assert center[0] > outside[0]
    assert outside[8] > center[8]
    assert center[-1] > outside[-1]


def test_every_lego_character_equips_with_switch_sound_and_color_wipe():
    expected = [p for p in (DEMOS / 'legacy/Characters').glob('*.yaml') if p.stem != 'true_jedi']
    expected += [DEMOS / f'{n}.yaml' for n in ('C3_hurt', 'yoda_hurt', 'darth_maul_hurt')]
    assert len(expected) == 11
    for profile in expected:
        weapon = load(profile)
        assert validate_runtime_payload(weapon) == [], profile
        clips = weapon['clips']
        if weapon['initial_state'] == 'equip':
            equip = actions(weapon, 'equip')
        else:
            equip = next(t['actions'] for t in weapon['transitions'] if t['trigger'] == 'on_equip')
        audios = [a for a in equip if a['type'] == 'play_audio']
        assert len(audios) == 1, profile
        audio_spec = clips[audios[0]['clip']]
        path = audio_spec if isinstance(audio_spec, str) else audio_spec['path']
        assert path == 'assets/audio/lego_util/lego-star-wars-switch-character-sound.wav', profile
        lights = [a for a in equip if a['type'] == 'play_light']
        assert len(lights) == 1, profile
        assert lights[0]['sequence'] == 'equip_wipe'
        assert lights[0]['mode'] == 'once'
        raw, compiled = sequence_for(weapon, 'equip_wipe')
        assert len(compiled.leds) == 61
        assert len(compiled.frames) == 16
        assert sum(f['duration_ms'] for f in raw['frames']) == 560
        # Spatial wipe begins left and finishes right, with a final fade.
        first = raw['frames'][0]['leds']
        middle = raw['frames'][8]['leds']
        last = raw['frames'][-1]['leds']
        assert first and middle
        assert not last


def test_all_exported_profiles_use_supported_audio_actions():
    for profiles in profiles_by_bank().values():
        for profile in profiles:
            weapon = load(profile)
            assert validate_runtime_payload(weapon) == [], profile
            for state in weapon['states']:
                for action in state.get('on_entry', []) + state.get('on_exit', []):
                    assert action['type'] not in {'play_sound', 'play_sound_random'}, profile
            for transition in weapon['transitions']:
                for action in transition.get('actions', []):
                    assert action['type'] not in {'play_sound', 'play_sound_random'}, profile
