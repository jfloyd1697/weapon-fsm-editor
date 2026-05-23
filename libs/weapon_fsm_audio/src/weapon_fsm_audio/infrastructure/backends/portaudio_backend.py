from __future__ import annotations

import abc
import math
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy import signal

from weapon_fsm_core.domain.enums import AudioMode
from weapon_fsm_hardware import AudioBackend, AudioPlayRequest


@dataclass(frozen=True)
class LoadedAudioClip:
    path: Path
    samples: np.ndarray
    sample_rate: int
    channel_count: int


@dataclass
class PlayingVoice:
    clip: str
    audio: LoadedAudioClip
    frame_index: int
    loop: bool


class PortAudioPlayer(abc.ABC):
    backend: PortAudioBackend

    def attach(self, backend: PortAudioBackend) -> None:
        self.backend = backend

    @abc.abstractmethod
    def play(self, request: AudioPlayRequest, *, loop: bool) -> None: ...

    @abc.abstractmethod
    def stop_clip(self, clip: str) -> None: ...

    @abc.abstractmethod
    def stop_all(self) -> None: ...

    @abc.abstractmethod
    def is_clip_playing(self, clip: str) -> bool: ...

    def close(self) -> None:
        self.stop_all()


class PortAudioBackend(AudioBackend):
    def __init__(
        self,
        *,
        player: PortAudioPlayer,
        volume: float = 1.0,
        device: int | str | None = None,
        sample_rate: int = 44100,
        channel_count: int = 2,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._volume = self._clamp_volume(volume)
        self._device = device
        self._sample_rate = sample_rate
        self._channel_count = channel_count
        self._log = log or (lambda message: None)
        self._cache: dict[Path, LoadedAudioClip] = {}
        self._queued_by_clip: dict[str, AudioPlayRequest] = {}
        self._lock = threading.RLock()
        self._player = player
        self._player.attach(self)

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def device(self) -> int | str | None:
        return self._device

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def channel_count(self) -> int:
        return self._channel_count

    def log(self, message: str) -> None:
        self._log(message)

    def preload(self, path: str | Path) -> None:
        self.load_clip(Path(path), match_backend_format=True)

    def preload_many(self, paths: list[str | Path]) -> None:
        for path in paths:
            self.preload(path)

    def stop_audio(self) -> None:
        self._queued_by_clip.clear()
        self._player.stop_all()
        self.log("[audio] stop all")

    def close(self) -> None:
        self._queued_by_clip.clear()
        self._player.close()

    def set_volume(self, volume: float) -> None:
        self._volume = self._clamp_volume(volume)

    def get_volume(self) -> float:
        return self._volume

    def load_clip(self, path: Path, *, match_backend_format: bool) -> LoadedAudioClip:
        resolved = path.resolve()
        cache_key = resolved if not match_backend_format else Path(f"{resolved}::{self._sample_rate}::{self._channel_count}")

        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        samples, file_sample_rate = sf.read(str(resolved), dtype="float32", always_2d=True)
        if len(samples) == 0:
            raise ValueError(f"Audio file is empty: {resolved}")

        sample_rate = int(file_sample_rate)
        if match_backend_format:
            samples = self._resample_if_needed(samples, sample_rate)
            samples = self._match_output_channels(samples)
            sample_rate = self._sample_rate

        loaded = LoadedAudioClip(
            path=resolved,
            samples=np.asarray(samples, dtype=np.float32),
            sample_rate=sample_rate,
            channel_count=int(samples.shape[1]),
        )

        with self._lock:
            self._cache[cache_key] = loaded

        return loaded

    def play_queued_if_ready(self, clip: str) -> None:
        with self._lock:
            still_playing = self._player.is_clip_playing(clip)
            pending = self._queued_by_clip.pop(clip, None)

        if pending is not None and not still_playing:
            self._player.play(pending, loop=pending.mode == AudioMode.LOOP)

    def _play_once(self, request: AudioPlayRequest) -> None:
        self._player.play(request, loop=False)

    def _play_loop(self, request: AudioPlayRequest) -> None:
        self._player.play(request, loop=True)

    def _stop_clip(self, clip: str) -> None:
        self._player.stop_clip(clip)

    def _is_clip_playing(self, clip: str) -> bool:
        return self._player.is_clip_playing(clip)

    def _queue_audio(self, request: AudioPlayRequest) -> None:
        self._queued_by_clip[request.clip] = request

    def _on_audio_ignored(self, request: AudioPlayRequest) -> None:
        self.log(f"[audio] ignoring play for busy clip '{request.clip}'")

    def _on_audio_queued(self, request: AudioPlayRequest) -> None:
        self.log(f"[audio] queued clip '{request.clip}'")

    def _resample_if_needed(self, samples: np.ndarray, source_sample_rate: int) -> np.ndarray:
        if source_sample_rate == self._sample_rate:
            return samples

        self.log(f"[audio] resampling from {source_sample_rate} Hz to {self._sample_rate} Hz")
        gcd = math.gcd(source_sample_rate, self._sample_rate)
        resampled = signal.resample_poly(samples, self._sample_rate // gcd, source_sample_rate // gcd, axis=0)
        if len(resampled) == 0:
            raise ValueError("Resampled audio would be empty")
        return np.asarray(resampled, dtype=np.float32)

    def _match_output_channels(self, samples: np.ndarray) -> np.ndarray:
        input_channels = samples.shape[1]
        if input_channels == self._channel_count:
            return samples
        if input_channels == 1 and self._channel_count == 2:
            return np.repeat(samples, 2, axis=1)
        if input_channels == 2 and self._channel_count == 1:
            return samples.mean(axis=1, keepdims=True)
        if input_channels > self._channel_count:
            return samples[:, : self._channel_count]
        padding = np.zeros((len(samples), self._channel_count - input_channels), dtype=np.float32)
        return np.concatenate([samples, padding], axis=1)

    def _clamp_volume(self, volume: float) -> float:
        return max(0.0, min(1.0, float(volume)))


class _PlayingStream:
    def __init__(self, *, clip: str, stream: sd.OutputStream, stop_event: threading.Event) -> None:
        self.clip = clip
        self.stream = stream
        self.stop_event = stop_event

    def stop(self) -> None:
        self.stop_event.set()
        try:
            self.stream.stop()
        finally:
            self.stream.close()

    def is_playing(self) -> bool:
        return bool(self.stream.active)


class PortAudioStreamPlayer(PortAudioPlayer):
    def __init__(self) -> None:
        self._active_by_clip: dict[str, list[_PlayingStream]] = {}
        self._lock = threading.RLock()

    def play(self, request: AudioPlayRequest, *, loop: bool) -> None:
        path = Path(request.path)
        if not path.exists():
            self.backend.log(f"[audio] missing file for clip '{request.clip}': {path}")
            return

        loaded = self.backend.load_clip(path, match_backend_format=False)
        stop_event = threading.Event()
        frame_index = 0

        def callback(outdata, frames, time, status) -> None:
            nonlocal frame_index
            if stop_event.is_set():
                outdata.fill(0)
                raise sd.CallbackStop()
            write_index = 0
            while write_index < frames:
                remaining_output = frames - write_index
                remaining_clip = len(loaded.samples) - frame_index
                if remaining_clip <= 0:
                    if not loop:
                        outdata[write_index:].fill(0)
                        raise sd.CallbackStop()
                    frame_index = 0
                    remaining_clip = len(loaded.samples)
                count = min(remaining_output, remaining_clip)
                outdata[write_index : write_index + count] = loaded.samples[frame_index : frame_index + count] * self.backend.volume
                write_index += count
                frame_index += count

        stream = sd.OutputStream(
            samplerate=loaded.sample_rate,
            channels=loaded.channel_count,
            dtype="float32",
            device=self.backend.device,
            callback=callback,
            finished_callback=lambda: self._on_finished(request.clip),
        )
        playing = _PlayingStream(clip=request.clip, stream=stream, stop_event=stop_event)
        with self._lock:
            self._active_by_clip.setdefault(request.clip, []).append(playing)
        stream.start()

    def stop_clip(self, clip: str) -> None:
        with self._lock:
            active = self._active_by_clip.pop(clip, [])
        for playing in active:
            playing.stop()

    def stop_all(self) -> None:
        with self._lock:
            active = [playing for group in self._active_by_clip.values() for playing in group]
            self._active_by_clip.clear()
        for playing in active:
            playing.stop()

    def is_clip_playing(self, clip: str) -> bool:
        with self._lock:
            active = [item for item in self._active_by_clip.get(clip, []) if item.is_playing()]
            self._active_by_clip[clip] = active
            return bool(active)

    def _on_finished(self, clip: str) -> None:
        with self._lock:
            active = [item for item in self._active_by_clip.get(clip, []) if item.is_playing()]
            self._active_by_clip[clip] = active
        self.backend.play_queued_if_ready(clip)


class PortAudioMixerPlayer(PortAudioPlayer):
    def __init__(self, *, block_size: int = 512, latency: str | float = "high") -> None:
        self._block_size = block_size
        self._latency = latency
        self._voices: list[PlayingVoice] = []
        self._lock = threading.RLock()
        self._stream: sd.OutputStream | None = None
        self._finished_clips: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._control_thread_stop = threading.Event()
        self._control_thread: threading.Thread | None = None

    def attach(self, backend: PortAudioBackend) -> None:
        super().attach(backend)
        self._control_thread_stop.clear()
        self._control_thread = threading.Thread(target=self._run_control_thread, name="PortAudioMixerControl", daemon=True)
        self._control_thread.start()
        self._stream = self._create_stream()
        self._stream.start()
        self.backend.log(
            f"[audio] mixer started sample_rate={self.backend.sample_rate} channels={self.backend.channel_count} "
            f"block_size={self._block_size} latency={self._latency}"
        )

    def play(self, request: AudioPlayRequest, *, loop: bool) -> None:
        path = Path(request.path)
        if not path.exists():
            self.backend.log(f"[audio] missing file for clip '{request.clip}': {path}")
            return
        loaded = self.backend.load_clip(path, match_backend_format=True)
        with self._lock:
            self._voices.append(PlayingVoice(clip=request.clip, audio=loaded, frame_index=0, loop=loop))

    def stop_clip(self, clip: str) -> None:
        with self._lock:
            self._voices = [voice for voice in self._voices if voice.clip != clip]

    def stop_all(self) -> None:
        with self._lock:
            self._voices.clear()

    def is_clip_playing(self, clip: str) -> bool:
        with self._lock:
            return any(voice.clip == clip for voice in self._voices)

    def close(self) -> None:
        self.stop_all()
        self._control_thread_stop.set()
        if self._control_thread is not None:
            self._control_thread.join(timeout=1.0)
            self._control_thread = None
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.backend.log("[audio] mixer closed")

    def _create_stream(self) -> sd.OutputStream:
        return sd.OutputStream(
            samplerate=self.backend.sample_rate,
            channels=self.backend.channel_count,
            dtype="float32",
            blocksize=self._block_size,
            latency=self._latency,
            device=self.backend.device,
            callback=self._audio_callback,
        )

    def _run_control_thread(self) -> None:
        while not self._control_thread_stop.is_set():
            try:
                clip = self._finished_clips.get(timeout=0.05)
            except queue.Empty:
                continue
            self.backend.play_queued_if_ready(clip)

    def _audio_callback(self, outdata, frames, time, status) -> None:
        mix = np.zeros((frames, self.backend.channel_count), dtype=np.float32)
        finished_clips: list[str] = []
        with self._lock:
            remaining_voices: list[PlayingVoice] = []
            for voice in self._voices:
                if self._mix_voice_into_buffer(voice=voice, mix=mix, frames=frames):
                    remaining_voices.append(voice)
                else:
                    finished_clips.append(voice.clip)
            self._voices = remaining_voices
        if self.backend.volume != 1.0:
            mix *= self.backend.volume
        np.clip(mix, -1.0, 1.0, out=mix)
        outdata[:] = mix
        for clip in finished_clips:
            self._finished_clips.put(clip)

    def _mix_voice_into_buffer(self, *, voice: PlayingVoice, mix: np.ndarray, frames: int) -> bool:
        write_index = 0
        samples = voice.audio.samples
        while write_index < frames:
            remaining_output = frames - write_index
            remaining_clip = len(samples) - voice.frame_index
            if remaining_clip <= 0:
                if not voice.loop:
                    return False
                voice.frame_index = 0
                remaining_clip = len(samples)
            count = min(remaining_output, remaining_clip)
            mix[write_index : write_index + count] += samples[voice.frame_index : voice.frame_index + count]
            write_index += count
            voice.frame_index += count
        return True
