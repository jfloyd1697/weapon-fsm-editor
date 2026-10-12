from __future__ import annotations

import math
import shutil
import struct
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from weapon_fsm_workspace.audio_export import export_audio_wav


def write_pcm(path: Path, rate: int, channels: int) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        frames = []
        for index in range(rate // 20):
            sample = int(12000 * math.sin(2 * math.pi * 440 * index / rate))
            frames.append(struct.pack("<h", sample) * channels)
        output.writeframes(b"".join(frames))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
@pytest.mark.parametrize("rate,channels", [(11025, 1), (12000, 1), (22050, 1), (24000, 1), (44100, 2)])
def test_export_normalizes_wav(tmp_path: Path, rate: int, channels: int) -> None:
    source = tmp_path / "source.wav"
    destination = tmp_path / "audio" / "shot.wav"
    write_pcm(source, rate, channels)
    original = source.read_bytes()

    export_audio_wav(source, destination)

    assert source.read_bytes() == original
    with wave.open(str(destination), "rb") as output:
        assert output.getframerate() == 44100
        assert output.getnchannels() == 1
        assert output.getsampwidth() == 2
        assert output.getcomptype() == "NONE"
        assert 2100 <= output.getnframes() <= 2310


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_bad_audio_fails_without_overwriting_old_export(tmp_path: Path) -> None:
    source = tmp_path / "bad.wav"
    source.write_bytes(b"not a wav")
    destination = tmp_path / "shot.wav"
    destination.write_bytes(b"previous good export")
    with pytest.raises(ValueError, match="Could not convert audio clip"):
        export_audio_wav(source, destination)
    assert destination.read_bytes() == b"previous good export"
    assert not list(tmp_path.glob(".audio-*"))


def test_missing_ffmpeg_has_actionable_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("weapon_fsm_workspace.audio_export.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="requires ffmpeg"):
        export_audio_wav(tmp_path / "input.wav", tmp_path / "output.wav")
