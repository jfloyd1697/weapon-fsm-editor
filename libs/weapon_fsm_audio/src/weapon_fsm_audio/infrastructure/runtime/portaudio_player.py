import queue
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd

from weapon_fsm_audio.infrastructure.runtime import PortAudioBackend
from weapon_fsm_audio.infrastructure.runtime.portaudio_backend import PortAudioPlayer, PlayingVoice
from weapon_fsm_hardware import AudioPlayRequest


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

            if status:
                self.backend.log(f"[audio] stream status for clip '{request.clip}': {status}")

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
                chunk = loaded.samples[frame_index:frame_index + count]

                outdata[write_index:write_index + count] = chunk * self.backend.volume

                write_index += count
                frame_index += count

        def finished_callback() -> None:
            self._on_finished(request.clip)

        stream = sd.OutputStream(
            samplerate=loaded.sample_rate,
            channels=loaded.channel_count,
            dtype="float32",
            device=self.backend.device,
            callback=callback,
            finished_callback=finished_callback,
        )

        playing = _PlayingStream(
            clip=request.clip,
            stream=stream,
            stop_event=stop_event,
        )

        with self._lock:
            self._active_by_clip.setdefault(request.clip, []).append(playing)

        stream.start()

        self.backend.log(
            f"[audio] stream play clip={request.clip} "
            f"mode={request.mode.value} "
            f"interrupt={request.interrupt.value} "
            f"path={path}"
        )

    def stop_clip(self, clip: str) -> None:
        with self._lock:
            active = self._active_by_clip.pop(clip, [])

        for playing in active:
            playing.stop()

        self.backend.log(f"[audio] stop clip '{clip}'")

    def stop_all(self) -> None:
        with self._lock:
            active = [
                playing
                for group in self._active_by_clip.values()
                for playing in group
            ]
            self._active_by_clip.clear()

        for playing in active:
            playing.stop()

    def is_clip_playing(self, clip: str) -> bool:
        with self._lock:
            active = self._active_by_clip.get(clip, [])
            active = [item for item in active if item.is_playing()]
            self._active_by_clip[clip] = active
            return bool(active)

    def _on_finished(self, clip: str) -> None:
        with self._lock:
            active = [
                item
                for item in self._active_by_clip.get(clip, [])
                if item.is_playing()
            ]
            self._active_by_clip[clip] = active

        self.backend.play_queued_if_ready(clip)


class PortAudioMixerPlayer(PortAudioPlayer):
    """
    Low-latency PortAudio player using one persistent OutputStream.

    The audio callback only does real-time-safe work:
        - mix active voices
        - write output samples
        - enqueue finished clip names

    It does not:
        - load files
        - log
        - start queued audio directly
        - call higher-level backend methods directly

    Finished clips are handled by a small control thread so scheduled audio can
    start outside the PortAudio callback.
    """

    def __init__(
        self,
        *,
        block_size: int = 512,
        latency: str | float = "high",
    ) -> None:
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
        self._control_thread = threading.Thread(
            target=self._run_control_thread,
            name="PortAudioMixerControl",
            daemon=True,
        )
        self._control_thread.start()

        self._stream = self._create_stream()
        self._stream.start()

        self.backend.log(
            f"[audio] mixer started "
            f"sample_rate={self.backend.sample_rate} "
            f"channels={self.backend.channel_count} "
            f"block_size={self._block_size} "
            f"latency={self._latency}"
        )

    def play(self, request: AudioPlayRequest, *, loop: bool) -> None:
        path = Path(request.path)

        if not path.exists():
            self.backend.log(f"[audio] missing file for clip '{request.clip}': {path}")
            return

        loaded = self.backend.load_clip(path, match_backend_format=True)

        with self._lock:
            self._voices.append(
                PlayingVoice(
                    clip=request.clip,
                    audio=loaded,
                    frame_index=0,
                    loop=loop,
                )
            )

        self.backend.log(
            f"[audio] mixer play clip={request.clip} "
            f"mode={request.mode.value} "
            f"interrupt={request.interrupt.value} "
            f"path={path}"
        )

    def stop_clip(self, clip: str) -> None:
        with self._lock:
            self._voices = [
                voice
                for voice in self._voices
                if voice.clip != clip
            ]

        self.backend.log(f"[audio] stop clip '{clip}'")

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
        # Do not log from here.
        # The PortAudio callback needs to stay as small and predictable as possible.

        mix = np.zeros((frames, self.backend.channel_count), dtype=np.float32)
        finished_clips: list[str] = []

        with self._lock:
            remaining_voices: list[PlayingVoice] = []

            for voice in self._voices:
                still_active = self._mix_voice_into_buffer(
                    voice=voice,
                    mix=mix,
                    frames=frames,
                )

                if still_active:
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

    def _mix_voice_into_buffer(
        self,
        *,
        voice: PlayingVoice,
        mix: np.ndarray,
        frames: int,
    ) -> bool:
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

            chunk = samples[voice.frame_index:voice.frame_index + count]
            mix[write_index:write_index + count] += chunk

            write_index += count
            voice.frame_index += count

        return True


class _PlayingStream:
    def __init__(
            self,
            *,
            clip: str,
            stream: sd.OutputStream,
            stop_event: threading.Event,
    ) -> None:
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
