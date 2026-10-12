import abc
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf
from scipy import signal

from weapon_fsm_hardware import AudioBackend, AudioPlayRequest


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print(method.__name__, te - ts)
        return result

    return timed


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
    def attach(self, backend: "PortAudioBackend") -> None:
        self.backend = backend

    @abc.abstractmethod
    def play(self, request: AudioPlayRequest, *, loop: bool) -> None:
        pass

    @abc.abstractmethod
    def stop_clip(self, clip: str) -> None:
        pass

    @abc.abstractmethod
    def stop_all(self) -> None:
        pass

    @abc.abstractmethod
    def is_clip_playing(self, clip: str) -> bool:
        pass

    def close(self) -> None:
        self.stop_all()


class Lock:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False



class PortAudioBackend(AudioBackend):

    @classmethod
    def set_default_player(cls, player: PortAudioPlayer) -> None:
        cls._player = player

    def __init__(
            self,
            *,
            player: PortAudioPlayer = None,
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

        if player is not None:
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
        self.load_clip(Path(path))

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

    @timeit
    def load_clip(
            self,
            path: Path,
            *,
            match_backend_format: bool = False,
    ) -> LoadedAudioClip:
        resolved = path.resolve()

        with self._lock:
            cached = self._cache.get(resolved)
            if cached is not None:
                return cached

        samples, file_sample_rate = sf.read(
            str(resolved),
            dtype="float32",
            always_2d=True,
        )

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
            self._cache[resolved] = loaded

        return loaded

    @timeit
    def play_queued_if_ready(self, clip: str) -> None:
        with self._lock:
            still_playing = self._player.is_clip_playing(clip)
            pending = self._queued_by_clip.pop(clip, None)

        if pending is not None and not still_playing:
            self.play_audio(
                clip=pending.clip,
                path=pending.path,
                mode=pending.mode,
                interrupt="interrupt",
            )

    @timeit
    def _play_once(self, request: AudioPlayRequest) -> None:
        self._player.play(request, loop=False)

    @timeit
    def _play_loop(self, request: AudioPlayRequest) -> None:
        self._player.play(request, loop=True)

    @timeit
    def _stop_clip(self, clip: str) -> None:
        self._player.stop_clip(clip)

    @timeit
    def _is_clip_playing(self, clip: str) -> bool:
        return self._player.is_clip_playing(clip)

    @timeit
    def _queue_audio(self, request: AudioPlayRequest) -> None:
        self._queued_by_clip[request.clip] = request

    def _on_audio_ignored(self, request: AudioPlayRequest) -> None:
        self.log(f"[audio] ignoring play for busy clip '{request.clip}'")

    def _on_audio_queued(self, request: AudioPlayRequest) -> None:
        self.log(f"[audio] queued clip '{request.clip}'")

    def _resample_if_needed(
            self,
            samples: np.ndarray,
            source_sample_rate: int,
    ) -> np.ndarray:
        if source_sample_rate == self._sample_rate:
            return samples

        self.log(
            f"[audio] resampling from "
            f"{source_sample_rate} Hz to {self._sample_rate} Hz"
        )

        gcd = math.gcd(source_sample_rate, self._sample_rate)
        up = self._sample_rate // gcd
        down = source_sample_rate // gcd

        resampled = signal.resample_poly(
            samples,
            up,
            down,
            axis=0,
        )

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
            return samples[:, :self._channel_count]

        missing = self._channel_count - input_channels
        padding = np.zeros((len(samples), missing), dtype=np.float32)
        return np.concatenate([samples, padding], axis=1)

    def _clamp_volume(self, volume: float) -> float:
        return max(0.0, min(1.0, float(volume)))
