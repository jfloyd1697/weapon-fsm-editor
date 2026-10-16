"""Check Memes bank profiles against compiled MCU assets and their audio timelines."""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np
import pytest
import yaml

from weapon_fsm_workspace.merged_sd import _load_sequence, profiles_by_bank
from weapon_fsm_workspace.runtime_validation import validate_runtime_payload

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / 'assets/profiles/legacy/Memes'


@pytest.mark.parametrize('name', ['faaah', 'bwowowow'])
def test_profile_uses_compiled_fsm_action_vocabulary(name: str) -> None:
    weapon = yaml.safe_load((PROFILES / f'{name}.yaml').read_text(encoding='utf-8'))['weapon']
    assert validate_runtime_payload(weapon) == []
    assert weapon['initial_state'] == 'ready'
    assert len(weapon['states']) == 1
    assert len(weapon['transitions']) == 1
    transition = weapon['transitions'][0]
    assert transition['trigger'] == 'trigger_pressed'
    assert transition['internal'] is True
    assert [action['type'] for action in transition['actions']] == ['play_audio', 'play_light']
    assert weapon['clips']['sound']['path'] == f'assets/audio/memes/{name}.wav'
    assert weapon['light_sequences']['sound_reactive']['path'] == f'assets/lights/memes/{name}.yaml'


@pytest.mark.parametrize('name', ['faaah', 'bwowowow'])
def test_sound_synchronized_light_sequence(name: str) -> None:
    sound = ROOT / f'assets/audio/memes/{name}.wav'
    with wave.open(str(sound), 'rb') as source:
        assert (source.getframerate(), source.getnchannels(), source.getsampwidth()) == (44100, 1, 2)
        audio = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(float) / 32768
    sequence_path = ROOT / f'assets/lights/memes/{name}.yaml'
    authored = yaml.safe_load(sequence_path.read_text(encoding='utf-8'))
    asset = _load_sequence(sequence_path, 'sound_reactive')
    assert len(asset.leds) == 61
    assert len(asset.frames) == len(authored['frames'])
    assert len(asset.frames) > 40
    assert not authored['frames'][-1]['leds']

    position_ms = 0
    audio_rms = []
    light_energy = []
    colors = set()
    distinct_patterns = set()
    for frame in authored['frames'][:-1]:
        next_ms = position_ms + frame['duration_ms']
        window = audio[round(position_ms * 44.1):round(next_ms * 44.1)]
        audio_rms.append(math.sqrt(float(np.mean(window * window))) if len(window) else 0)
        light_energy.append(sum(light['intensity'] for light in frame['leds'].values()) / 61)
        colors.update(light['color'] for light in frame['leds'].values())
        distinct_patterns.add(tuple(round(frame['leds'].get(str(i), {}).get('intensity', 0), 1) for i in range(61)))
        position_ms = next_ms

    # Light frames align to the decoded WAV duration, not an arbitrary fixed effect length.
    assert abs(position_ms - len(audio) / 44.1) <= 1
    assert len(colors) >= 8
    assert len(distinct_patterns) >= 15
    assert float(np.corrcoef(audio_rms, light_energy)[0, 1]) >= 0.75
    assert max(light_energy[:4]) < max(light_energy) * 0.25
    assert sum(frame['duration_ms'] for frame in authored['frames']) - position_ms == 40


def test_memes_exported_as_independent_bank() -> None:
    banks = profiles_by_bank()
    assert {profile.stem for profile in banks['Memes']} == {'faaah', 'bwowowow'}
    assert len(banks['Farts']) == 8
