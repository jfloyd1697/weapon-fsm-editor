import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, QUrl

from weapon_fsm_hardware import AudioBackend, LightBackend

try:
    from PyQt6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover - depends on local Qt install
    QSoundEffect = None  # type: ignore[assignment]
    warnings.warn("QtMultimedia is unavailable; cannot play audio")


@dataclass(frozen=True)
class _PlayRequest:
    clip: str
    path: str
    mode: str
    interrupt: str


class QAudioBackendMeta(type(QObject), type(AudioBackend)):
    pass



class QtAudioBackend(QObject, AudioBackend, metaclass=QAudioBackendMeta):
    def __init__(self, log: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._log = log or (lambda message: None)
        self._active_by_clip: dict[str, list[QSoundEffect]] = {}
        self._queued_by_clip: dict[str, _PlayRequest] = {}

    def play_audio(
        self,
        *,
        clip: str,
        path: str,
        mode: str,
        interrupt: str,
    ) -> None:
        if QSoundEffect is None:
            self._log(f"[audio] QtMultimedia is unavailable; cannot play {clip}")
            return

        resolved = Path(path)
        if not resolved.exists():
            self._log(f"[audio] missing file for clip '{clip}': {resolved}")
            return

        active = self._active_by_clip.setdefault(clip, [])
        currently_playing = [effect for effect in active if effect.isPlaying()]
        self._active_by_clip[clip] = currently_playing

        if interrupt == "ignore" and currently_playing:
            self._log(f"[audio] ignoring play for busy clip '{clip}'")
            return

        if interrupt == "schedule" and currently_playing:
            self._queued_by_clip[clip] = _PlayRequest(
                clip=clip,
                path=str(resolved),
                mode=mode,
                interrupt=interrupt,
            )
            self._log(f"[audio] queued clip '{clip}'")
            return

        if interrupt == "interrupt":
            self._stop_clip(clip)

        effect = QSoundEffect(self)
        effect.setSource(QUrl.fromLocalFile(str(resolved)))
        effect.setLoopCount(-1 if mode == "loop" else 1)
        effect.playingChanged.connect(
            lambda clip_name=clip, current=effect: self._on_playing_changed(clip_name, current)
        )
        effect.statusChanged.connect(
            lambda clip_name=clip, current=effect: self._on_status_changed(clip_name, current)
        )
        self._active_by_clip.setdefault(clip, []).append(effect)
        effect.play()
        self._log(f"[audio] play clip={clip} mode={mode} interrupt={interrupt} path={resolved}")

    def stop_audio(self) -> None:
        for clip in list(self._active_by_clip):
            self._stop_clip(clip)
        self._queued_by_clip.clear()
        self._log("[audio] stop all")

    def stop_clip(self, clip: str) -> None:
        self._stop_clip(clip)
        self._queued_by_clip.pop(clip, None)
        self._log(f"[audio] stop clip={clip}")

    def _stop_clip(self, clip: str) -> None:
        for effect in self._active_by_clip.get(clip, []):
            effect.stop()
        self._active_by_clip[clip] = []

    def _on_playing_changed(self, clip: str, effect) -> None:  # noqa: ANN001
        active = self._active_by_clip.get(clip, [])
        self._active_by_clip[clip] = [item for item in active if item is not effect and item.isPlaying()]
        if effect.isPlaying():
            self._active_by_clip.setdefault(clip, []).append(effect)
            return

        queued = self._queued_by_clip.pop(clip, None)
        if queued is not None:
            self.play_audio(
                clip=queued.clip,
                path=queued.path,
                mode=queued.mode,
                interrupt="interrupt",
            )

    def _on_status_changed(self, clip: str, effect) -> None:  # noqa: ANN001
        if QSoundEffect is None:
            return
        if effect.status() == QSoundEffect.Status.Error:
            self._log(f"[audio] Qt reported an error while playing '{clip}'")
