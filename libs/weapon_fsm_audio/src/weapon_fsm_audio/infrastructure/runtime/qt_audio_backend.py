from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, QUrl

from weapon_fsm_hardware import AudioBackend, AudioPlayRequest

try:
    from PyQt6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover - depends on local Qt install
    QSoundEffect = None  # type: ignore[assignment]


class QtAudioBackendMeta(type(AudioBackend), type(QObject)):
    pass


class QtAudioBackend(AudioBackend, QObject, metaclass=QtAudioBackendMeta):
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._log = log or (lambda message: None)
        self._active_by_clip: dict[str, list[QSoundEffect]] = {}
        self._queued_by_clip: dict[str, AudioPlayRequest] = {}

    def stop_audio(self) -> None:
        self._queued_by_clip.clear()

        for clip in list(self._active_by_clip):
            self._stop_clip(clip)

        self._log("[audio] stop all")

    def _play_once(self, request: AudioPlayRequest) -> None:
        self._play_with_loop_count(request, 1)

    def _play_loop(self, request: AudioPlayRequest) -> None:
        self._play_with_loop_count(request, 10000000)

    def _play_with_loop_count(self, request: AudioPlayRequest, loop_count: int) -> None:
        if QSoundEffect is None:
            self._log(f"[audio] QtMultimedia is unavailable; cannot play {request.clip}")
            return

        resolved = Path(request.path)
        if not resolved.exists():
            self._log(f"[audio] missing file for clip '{request.clip}': {resolved}")
            return

        effect = QSoundEffect(self)
        effect.setSource(QUrl.fromLocalFile(str(resolved)))
        effect.setLoopCount(loop_count)

        effect.playingChanged.connect(
            lambda clip_name=request.clip, current=effect: self._on_playing_changed(
                clip_name,
                current,
            )
        )
        effect.statusChanged.connect(
            lambda clip_name=request.clip, current=effect: self._on_status_changed(
                clip_name,
                current,
            )
        )

        self._active_by_clip.setdefault(request.clip, []).append(effect)
        effect.play()

        self._log(
            f"[audio] play clip={request.clip} "
            f"mode={request.mode.value} "
            f"interrupt={request.interrupt.value} "
            f"path={resolved}"
        )

    def _stop_clip(self, clip: str) -> None:
        for effect in self._active_by_clip.get(clip, []):
            effect.stop()
            effect.deleteLater()

        self._active_by_clip[clip] = []

    def _is_clip_playing(self, clip: str) -> bool:
        active = self._active_by_clip.setdefault(clip, [])
        currently_playing = [effect for effect in active if effect.isPlaying()]
        self._active_by_clip[clip] = currently_playing
        return bool(currently_playing)

    def _queue_audio(self, request: AudioPlayRequest) -> None:
        self._queued_by_clip[request.clip] = request

    def _on_audio_ignored(self, request: AudioPlayRequest) -> None:
        self._log(f"[audio] ignoring play for busy clip '{request.clip}'")

    def _on_audio_queued(self, request: AudioPlayRequest) -> None:
        self._log(f"[audio] queued clip '{request.clip}'")

    def _on_playing_changed(self, clip: str, effect: QSoundEffect) -> None:
        if effect.isPlaying():
            return

        active = [
            item
            for item in self._active_by_clip.get(clip, [])
            if item is not effect and item.isPlaying()
        ]
        self._active_by_clip[clip] = active
        effect.deleteLater()

        pending = self._queued_by_clip.pop(clip, None)
        if pending is not None and not active:
            self.play_audio(
                clip=pending.clip,
                path=pending.path,
                mode=pending.mode,
                interrupt="interrupt",
            )

    def _on_status_changed(self, clip: str, effect: QSoundEffect) -> None:
        if effect.status() == QSoundEffect.Status.Error:
            self._log(f"[audio] failed to load clip '{clip}'")