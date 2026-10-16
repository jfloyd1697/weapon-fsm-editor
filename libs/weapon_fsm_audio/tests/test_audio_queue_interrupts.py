"""PortAudio control-plane interruption tests; no sound device is opened."""

from pathlib import Path

from weapon_fsm_audio.infrastructure.runtime.portaudio_backend import PortAudioBackend, PortAudioPlayer
from weapon_fsm_core.domain.enums import AudioInterrupt, AudioMode
from weapon_fsm_hardware.backends import AudioPlayRequest


class Player(PortAudioPlayer):
    def __init__(self) -> None:
        self.played: list[tuple[str, bool]] = []
        self.stopped: list[str] = []
        self.active: set[str] = set()

    def play(self, request: AudioPlayRequest, *, loop: bool) -> None:
        self.played.append((request.clip, loop))
        self.active.add(request.clip)

    def stop_clip(self, clip: str) -> None:
        self.stopped.append(clip)
        self.active.discard(clip)

    def stop_all(self) -> None:
        self.active.clear()

    def is_clip_playing(self, clip: str) -> bool:
        return clip in self.active


def backend() -> tuple[PortAudioBackend, Player]:
    player = Player()
    return PortAudioBackend(player=player), player


def test_scheduled_clip_survives_callbacks_while_current_audio_is_playing() -> None:
    audio, player = backend()
    audio._queued_by_clip["click"] = AudioPlayRequest("click", "unused.wav", AudioMode.ONCE, AudioInterrupt.SCHEDULE)
    player.active.add("click")
    audio.play_queued_if_ready("click")
    assert "click" in audio._queued_by_clip
    player.active.clear()
    audio.play_queued_if_ready("click")
    assert player.played == [("click", False)]
    assert not audio._queued_by_clip


def test_new_interrupt_cancels_stale_scheduled_audio() -> None:
    audio, player = backend()
    audio._queued_by_clip["click"] = AudioPlayRequest("click", "unused.wav", AudioMode.ONCE, AudioInterrupt.SCHEDULE)
    player.active.add("click")
    audio.play_audio(clip="click", path="current.wav", interrupt="interrupt")
    assert player.stopped == ["click"]
    assert player.played == [("click", False)]
    assert "click" not in audio._queued_by_clip


def test_interrupt_all_clears_active_and_scheduled_audio() -> None:
    audio, player = backend()
    player.active.update(["one", "two"])
    audio._queued_by_clip["one"] = AudioPlayRequest("one", "unused.wav", AudioMode.ONCE, AudioInterrupt.SCHEDULE)
    audio.play_audio(clip="three", path="new.wav", interrupt="interrupt_all")
    assert player.active == {"three"}
    assert audio._queued_by_clip == {}


def test_ignore_does_not_replace_busy_audio() -> None:
    audio, player = backend()
    player.active.add("click")
    audio.play_audio(clip="click", path="new.wav", interrupt="ignore")
    assert not player.played
    assert player.active == {"click"}


def test_audio_cache_separates_source_and_output_format(tmp_path: Path, monkeypatch) -> None:
    import numpy as np
    from weapon_fsm_audio.infrastructure.runtime import portaudio_backend

    audio, _ = backend()
    readings: list[Path] = []

    def read(path: str, **kwargs):
        readings.append(Path(path))
        return np.zeros((100, 1), dtype=np.float32), audio.sample_rate

    monkeypatch.setattr(portaudio_backend.sf, "read", read)
    path = tmp_path / "audio.wav"
    raw = audio.load_clip(path, match_backend_format=False)
    output = audio.load_clip(path, match_backend_format=True)
    assert raw.channel_count == 1
    assert output.channel_count == 2
    assert len(readings) == 2
    assert audio.load_clip(path, match_backend_format=True) is output
    assert len(readings) == 2
