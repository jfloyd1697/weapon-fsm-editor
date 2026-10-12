import abc
from dataclasses import dataclass

from weapon_fsm_core.domain.enums import AudioInterrupt, AudioMode, LightMode


@dataclass(frozen=True)
class AudioPlayRequest:
    clip: str
    path: str
    mode: AudioMode
    interrupt: AudioInterrupt


class AudioBackend(abc.ABC):
    def play_audio(
        self,
        *,
        clip: str,
        path: str,
        mode: AudioMode | str = AudioMode.ONCE,
        interrupt: AudioInterrupt | str = AudioInterrupt.OVERLAP,
    ) -> None:
        request = AudioPlayRequest(
            clip=clip,
            path=path,
            mode=self._coerce_mode(mode),
            interrupt=self._coerce_interrupt(interrupt),
        )

        if request.interrupt == AudioInterrupt.IGNORE and self._is_clip_playing(request.clip):
            self._on_audio_ignored(request)
            return

        if request.interrupt == AudioInterrupt.SCHEDULE and self._is_clip_playing(request.clip):
            self._queue_audio(request)
            self._on_audio_queued(request)
            return

        if request.interrupt == AudioInterrupt.INTERRUPT:
            self._stop_clip(request.clip)

        if request.interrupt == AudioInterrupt.INTERRUPT_ALL:
            self.stop_audio()

        if request.mode == AudioMode.LOOP:
            self._play_loop(request)
        else:
            self._play_once(request)

    @abc.abstractmethod
    def stop_audio(self) -> None: ...

    @abc.abstractmethod
    def _play_once(self, request: AudioPlayRequest) -> None: ...

    @abc.abstractmethod
    def _play_loop(self, request: AudioPlayRequest) -> None: ...

    @abc.abstractmethod
    def _stop_clip(self, clip: str) -> None: ...

    def _is_clip_playing(self, clip: str) -> bool:
        return False

    def _queue_audio(self, request: AudioPlayRequest) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support scheduled audio playback")

    def _on_audio_ignored(self, request: AudioPlayRequest) -> None:
        pass

    def _on_audio_queued(self, request: AudioPlayRequest) -> None:
        pass

    def _coerce_mode(self, mode: AudioMode | str) -> AudioMode:
        if isinstance(mode, AudioMode):
            return mode
        try:
            return AudioMode(str(mode).strip().lower())
        except ValueError:
            raise ValueError(f"Unsupported audio mode: {mode}") from None

    def _coerce_interrupt(self, interrupt: AudioInterrupt | str) -> AudioInterrupt:
        if isinstance(interrupt, AudioInterrupt):
            return interrupt
        try:
            return AudioInterrupt(str(interrupt).strip().lower())
        except ValueError:
            raise ValueError(f"Unsupported audio interrupt behavior: {interrupt}") from None


class LightBackend(abc.ABC):
    @abc.abstractmethod
    def play_light(
        self,
        *,
        sequence: str,
        path: str,
        mode: LightMode | str = LightMode.ONCE,
    ) -> None: ...

    @abc.abstractmethod
    def stop_light(self) -> None: ...
