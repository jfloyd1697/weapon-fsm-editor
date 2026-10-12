from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from weapon_fsm_lights import LightFrame, LightSequenceAsset, load_light_sequence


@dataclass(frozen=True)
class LightPlaybackState:
    sequence_name: str
    frame_index: int
    frame_count: int
    elapsed_frame_ms: int
    frame_duration_ms: int
    mode: str
    speed: float
    playing: bool


class LightAnimationPlayer(QObject):
    """
    Timer-based light sequence player for editor/runtime preview.

    The canvas renders frames; this object owns playback timing so animation
    tuning can be shared across preview panels and tools.
    """

    frame_changed = pyqtSignal(int, object)
    playback_state_changed = pyqtSignal(object)
    playback_finished = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._asset: LightSequenceAsset | None = None
        self._sequence_name = ""
        self._mode = "once"
        self._speed = 1.0
        self._frame_index = 0
        self._elapsed_frame_ms = 0
        self._playing = False

        self._timer = QTimer(self)
        self._timer.setInterval(1)
        self._timer.timeout.connect(self._tick)

    @property
    def asset(self) -> LightSequenceAsset | None:
        return self._asset

    @property
    def frame_index(self) -> int:
        return self._frame_index

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_playing(self) -> bool:
        return self._playing

    def load_path(
        self,
        path: str | Path,
        *,
        sequence_name: str | None = None,
        mode: str = "once",
        autoplay: bool = False,
    ) -> None:
        asset_path = Path(path).expanduser().resolve()
        self.set_asset(
            load_light_sequence(asset_path),
            sequence_name=sequence_name or asset_path.stem,
            mode=mode,
            autoplay=autoplay,
        )

    def set_asset(
        self,
        asset: LightSequenceAsset,
        *,
        sequence_name: str = "sequence",
        mode: str = "once",
        autoplay: bool = False,
    ) -> None:
        self.stop(reset_to_first_frame=False)
        self._asset = asset
        self._sequence_name = sequence_name
        self._mode = mode
        self._frame_index = 0
        self._elapsed_frame_ms = 0
        self._emit_current_frame()
        if autoplay:
            self.play()
        else:
            self._emit_state()

    def play(self) -> None:
        if self._asset is None or not self._asset.frames:
            return
        self._playing = True
        self._timer.start()
        self._emit_state()

    def pause(self) -> None:
        self._playing = False
        self._timer.stop()
        self._emit_state()

    def stop(self, *, reset_to_first_frame: bool = True) -> None:
        self._playing = False
        self._timer.stop()
        if reset_to_first_frame:
            self._frame_index = 0
            self._elapsed_frame_ms = 0
            self._emit_current_frame()
        self._emit_state()

    def clear(self) -> None:
        self._playing = False
        self._timer.stop()
        self._asset = None
        self._sequence_name = ""
        self._frame_index = 0
        self._elapsed_frame_ms = 0
        self._emit_state()

    def restart(self) -> None:
        self.seek_frame(0)
        self.play()

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.05, float(speed))
        self._emit_state()

    def set_mode(self, mode: str) -> None:
        self._mode = str(mode)
        self._emit_state()

    def seek_frame(self, frame_index: int) -> None:
        if self._asset is None or not self._asset.frames:
            return
        self._frame_index = max(0, min(int(frame_index), len(self._asset.frames) - 1))
        self._elapsed_frame_ms = 0
        self._emit_current_frame()
        self._emit_state()

    def step_next(self) -> None:
        self._advance_frame(manual=True)

    def step_previous(self) -> None:
        if self._asset is None or not self._asset.frames:
            return
        previous = self._frame_index - 1
        if previous < 0:
            previous = len(self._asset.frames) - 1 if self._mode == "loop" else 0
        self.seek_frame(previous)

    def current_frame(self) -> LightFrame | None:
        if self._asset is None or not self._asset.frames:
            return None
        return self._asset.frames[self._frame_index]

    def _tick(self) -> None:
        if self._asset is None or not self._asset.frames:
            self.pause()
            return
        frame = self._asset.frames[self._frame_index]
        self._elapsed_frame_ms += max(1, round(self._timer.interval() * self._speed))
        if self._elapsed_frame_ms >= max(1, frame.duration_ms):
            self._advance_frame(manual=False)
        self._emit_state()

    def _advance_frame(self, *, manual: bool) -> None:
        if self._asset is None or not self._asset.frames:
            return
        next_index = self._frame_index + 1
        if next_index >= len(self._asset.frames):
            if self._mode == "loop":
                next_index = 0
            else:
                next_index = len(self._asset.frames) - 1
                if not manual:
                    self.pause()
                    self.playback_finished.emit()
        self._frame_index = next_index
        self._elapsed_frame_ms = 0
        self._emit_current_frame()
        self._emit_state()

    def _emit_current_frame(self) -> None:
        frame = self.current_frame()
        if frame is not None:
            self.frame_changed.emit(self._frame_index, frame)

    def _emit_state(self) -> None:
        frame = self.current_frame()
        frame_count = len(self._asset.frames) if self._asset is not None else 0
        self.playback_state_changed.emit(
            LightPlaybackState(
                sequence_name=self._sequence_name,
                frame_index=self._frame_index,
                frame_count=frame_count,
                elapsed_frame_ms=self._elapsed_frame_ms,
                frame_duration_ms=frame.duration_ms if frame is not None else 0,
                mode=self._mode,
                speed=self._speed,
                playing=self._playing,
            )
        )
