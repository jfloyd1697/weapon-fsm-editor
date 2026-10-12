import json
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from qtpy import QtCore, QtGui, QtWidgets


@dataclass
class LoopRegion:
    start_sample: int
    end_sample: int


class LoopingAudioPlayer(QtCore.QObject):
    playback_started = QtCore.Signal()
    playback_stopped = QtCore.Signal()
    playback_position_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio = np.zeros((0, 1), dtype=np.float32)
        self._sample_rate = 44100
        self._loop = LoopRegion(0, 0)
        self._position = 0
        self._stream = None
        self._lock = threading.RLock()

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._emit_position)

    def set_audio(self, audio: np.ndarray, sample_rate: int):
        if audio.ndim == 1:
            audio = audio[:, np.newaxis]

        audio = np.asarray(audio, dtype=np.float32)

        with self._lock:
            self.stop()
            self._audio = audio
            self._sample_rate = int(sample_rate)
            self._position = 0
            self._loop = LoopRegion(0, len(audio))

    def set_loop_region(self, start_sample: int, end_sample: int):
        with self._lock:
            sample_count = len(self._audio)

            if sample_count <= 1:
                self._loop = LoopRegion(0, 0)
                self._position = 0
                return

            start_sample = max(0, min(int(start_sample), sample_count - 2))
            end_sample = max(start_sample + 1, min(int(end_sample), sample_count))
            self._loop = LoopRegion(start_sample, end_sample)

            if self._position >= end_sample:
                self._position = start_sample

    def seek_to_start(self):
        with self._lock:
            self._position = 0

    def seek(self, sample: int):
        with self._lock:
            if len(self._audio) == 0:
                self._position = 0
            else:
                self._position = max(0, min(int(sample), len(self._audio) - 1))

    def play(self):
        with self._lock:
            if self._stream is not None:
                return

            if len(self._audio) == 0:
                return

            channels = self._audio.shape[1]

            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=channels,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()

        self._timer.start()
        self.playback_started.emit()

    def stop(self):
        with self._lock:
            stream = self._stream
            self._stream = None

        if stream is not None:
            stream.stop()
            stream.close()

        self._timer.stop()
        self.playback_stopped.emit()

    def is_playing(self) -> bool:
        with self._lock:
            return self._stream is not None

    def _callback(self, outdata, frames, time_info, status):
        del time_info

        if status:
            pass

        with self._lock:
            audio = self._audio
            position = self._position
            loop_start = self._loop.start_sample
            loop_end = self._loop.end_sample

            if len(audio) == 0:
                outdata.fill(0)
                return

            write_index = 0

            while write_index < frames:
                if position >= loop_end:
                    position = loop_start

                readable = min(loop_end - position, frames - write_index)

                if readable <= 0:
                    position = loop_start
                    continue

                outdata[write_index:write_index + readable] = audio[position:position + readable]

                write_index += readable
                position += readable

            self._position = position

    def _emit_position(self):
        with self._lock:
            position = self._position

        self.playback_position_changed.emit(position)


class WaveformLoopWidget(QtWidgets.QWidget):
    loop_region_changed = QtCore.Signal(int, int)
    seek_requested = QtCore.Signal(int)

    MARKER_NONE = 0
    MARKER_START = 1
    MARKER_END = 2

    def __init__(self, parent=None):
        super().__init__(parent)

        self._audio = np.zeros((0,), dtype=np.float32)
        self._sample_rate = 44100
        self._loop_start = 0
        self._loop_end = 0
        self._playhead = 0

        self._dragging_marker = self.MARKER_NONE

        self.setMinimumHeight(260)
        self.setMouseTracking(True)

    def set_audio(self, audio: np.ndarray, sample_rate: int):
        if audio.ndim == 2:
            audio = audio.mean(axis=1)

        self._audio = np.asarray(audio, dtype=np.float32)
        self._sample_rate = int(sample_rate)
        self._loop_start = 0
        self._loop_end = len(self._audio)
        self._playhead = 0
        self.update()

    def set_loop_region(self, start_sample: int, end_sample: int):
        sample_count = len(self._audio)

        if sample_count <= 1:
            self._loop_start = 0
            self._loop_end = 0
            self.update()
            return

        self._loop_start = max(0, min(int(start_sample), sample_count - 2))
        self._loop_end = max(self._loop_start + 1, min(int(end_sample), sample_count))
        self.update()

    def loop_region(self) -> LoopRegion:
        return LoopRegion(self._loop_start, self._loop_end)

    def set_playhead(self, sample: int):
        self._playhead = int(sample)
        self.update()

    def paintEvent(self, event):
        del event

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)

        rect = self.rect()
        painter.fillRect(rect, QtGui.QColor(24, 24, 24))

        if len(self._audio) == 0:
            painter.setPen(QtGui.QColor(180, 180, 180))
            painter.drawText(rect, QtCore.Qt.AlignCenter, "Load an audio file")
            return

        waveform_rect = QtCore.QRect(
            10,
            10,
            rect.width() - 20,
            rect.height() - 90,
        )

        wrap_rect = QtCore.QRect(
            10,
            rect.height() - 70,
            rect.width() - 20,
            55,
        )

        self._draw_loop_region(painter, waveform_rect)
        self._draw_waveform(painter, waveform_rect, self._audio)
        self._draw_markers(painter, waveform_rect)
        self._draw_playhead(painter, waveform_rect)
        self._draw_wrap_preview(painter, wrap_rect)

    def mousePressEvent(self, event):
        if len(self._audio) == 0:
            return

        x = event.position().x() if hasattr(event, "position") else event.x()
        sample = self._x_to_sample(x)

        start_x = self._sample_to_x(self._loop_start)
        end_x = self._sample_to_x(self._loop_end)

        if abs(x - start_x) <= 8:
            self._dragging_marker = self.MARKER_START
        elif abs(x - end_x) <= 8:
            self._dragging_marker = self.MARKER_END
        else:
            self.seek_requested.emit(sample)

    def mouseMoveEvent(self, event):
        if len(self._audio) == 0:
            return

        x = event.position().x() if hasattr(event, "position") else event.x()
        sample = self._x_to_sample(x)

        if self._dragging_marker == self.MARKER_START:
            self._loop_start = max(0, min(sample, self._loop_end - 1))
            self.loop_region_changed.emit(self._loop_start, self._loop_end)
            self.update()

        elif self._dragging_marker == self.MARKER_END:
            self._loop_end = max(self._loop_start + 1, min(sample, len(self._audio)))
            self.loop_region_changed.emit(self._loop_start, self._loop_end)
            self.update()

    def mouseReleaseEvent(self, event):
        del event
        self._dragging_marker = self.MARKER_NONE

    def _waveform_rect(self) -> QtCore.QRect:
        return QtCore.QRect(10, 10, self.width() - 20, self.height() - 90)

    def _sample_to_x(self, sample: int) -> int:
        waveform_rect = self._waveform_rect()
        sample_count = max(1, len(self._audio) - 1)
        ratio = sample / sample_count
        return int(waveform_rect.left() + ratio * waveform_rect.width())

    def _x_to_sample(self, x: float) -> int:
        waveform_rect = self._waveform_rect()
        ratio = (x - waveform_rect.left()) / max(1, waveform_rect.width())
        ratio = max(0.0, min(1.0, ratio))
        return int(ratio * max(1, len(self._audio) - 1))

    def _draw_waveform(self, painter: QtGui.QPainter, rect: QtCore.QRect, audio: np.ndarray):
        painter.setPen(QtGui.QColor(210, 210, 210))

        width = max(1, rect.width())
        center_y = rect.center().y()
        half_height = rect.height() / 2.0

        samples_per_pixel = max(1, len(audio) // width)

        for x in range(width):
            start = x * samples_per_pixel
            end = min(len(audio), start + samples_per_pixel)

            if start >= end:
                continue

            chunk = audio[start:end]
            low = float(np.min(chunk))
            high = float(np.max(chunk))

            y1 = int(center_y - high * half_height)
            y2 = int(center_y - low * half_height)

            painter.drawLine(rect.left() + x, y1, rect.left() + x, y2)

        painter.setPen(QtGui.QColor(70, 70, 70))
        painter.drawRect(rect)

    def _draw_loop_region(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        start_x = self._sample_to_x(self._loop_start)
        end_x = self._sample_to_x(self._loop_end)

        loop_rect = QtCore.QRect(
            start_x,
            rect.top(),
            max(1, end_x - start_x),
            rect.height(),
        )

        painter.fillRect(loop_rect, QtGui.QColor(70, 100, 140, 70))

    def _draw_markers(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        start_x = self._sample_to_x(self._loop_start)
        end_x = self._sample_to_x(self._loop_end)

        start_color = QtGui.QColor(80, 220, 120)
        end_color = QtGui.QColor(240, 120, 80)

        self._draw_marker(painter, rect, start_x, start_color, "Loop Start")
        self._draw_marker(painter, rect, end_x, end_color, "Loop End")

    def _draw_marker(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
        x: int,
        color: QtGui.QColor,
        label: str,
    ):
        painter.setPen(QtGui.QPen(color, 2))
        painter.drawLine(x, rect.top(), x, rect.bottom())

        painter.fillRect(QtCore.QRect(x - 5, rect.top(), 10, 16), color)

        painter.setPen(QtGui.QColor(230, 230, 230))
        painter.drawText(x + 6, rect.top() + 14, label)

    def _draw_playhead(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        x = self._sample_to_x(self._playhead)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 1))
        painter.drawLine(x, rect.top(), x, rect.bottom())

    def _draw_wrap_preview(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        painter.fillRect(rect, QtGui.QColor(36, 36, 36))
        painter.setPen(QtGui.QColor(90, 90, 90))
        painter.drawRect(rect)

        painter.setPen(QtGui.QColor(180, 180, 180))
        painter.drawText(rect.left() + 6, rect.top() + 15, "Wrap preview: loop end -> loop start")

        preview_ms = 120
        preview_samples = int(self._sample_rate * preview_ms / 1000)

        before_start = max(0, self._loop_end - preview_samples)
        before_end = self._loop_end

        after_start = self._loop_start
        after_end = min(len(self._audio), self._loop_start + preview_samples)

        before = self._audio[before_start:before_end]
        after = self._audio[after_start:after_end]

        if len(before) == 0 or len(after) == 0:
            return

        middle_x = rect.center().x()

        before_rect = QtCore.QRect(
            rect.left() + 5,
            rect.top() + 20,
            rect.width() // 2 - 8,
            rect.height() - 25,
        )

        after_rect = QtCore.QRect(
            middle_x + 4,
            rect.top() + 20,
            rect.width() // 2 - 9,
            rect.height() - 25,
        )

        self._draw_small_waveform(painter, before_rect, before)
        self._draw_small_waveform(painter, after_rect, after)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 2))
        painter.drawLine(middle_x, rect.top() + 18, middle_x, rect.bottom() - 4)

    def _draw_small_waveform(self, painter: QtGui.QPainter, rect: QtCore.QRect, audio: np.ndarray):
        painter.setPen(QtGui.QColor(190, 190, 190))

        width = max(1, rect.width())
        center_y = rect.center().y()
        half_height = rect.height() / 2.0
        samples_per_pixel = max(1, len(audio) // width)

        for x in range(width):
            start = x * samples_per_pixel
            end = min(len(audio), start + samples_per_pixel)

            if start >= end:
                continue

            chunk = audio[start:end]
            low = float(np.min(chunk))
            high = float(np.max(chunk))

            y1 = int(center_y - high * half_height)
            y2 = int(center_y - low * half_height)

            painter.drawLine(rect.left() + x, y1, rect.left() + x, y2)


class LoopSampleEditorWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._player = LoopingAudioPlayer(self)

        self.waveform = WaveformLoopWidget(self)

        self.open_button = QtWidgets.QPushButton("Open Audio")
        self.save_session_button = QtWidgets.QPushButton("Save Session")
        self.load_session_button = QtWidgets.QPushButton("Load Session")
        self.export_segments_button = QtWidgets.QPushButton("Export Loop Segments")
        self.extend_audio_button = QtWidgets.QPushButton("Extend Audio")
        self.play_button = QtWidgets.QPushButton("Play")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.reset_button = QtWidgets.QPushButton("Reset Loop")

        self.start_label = QtWidgets.QLabel("Start: 0")
        self.end_label = QtWidgets.QLabel("End: 0")

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.open_button)
        controls.addWidget(self.save_session_button)
        controls.addWidget(self.load_session_button)
        controls.addWidget(self.export_segments_button)
        controls.addWidget(self.play_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.reset_button)
        controls.addWidget(self.extend_audio_button)
        controls.addStretch()
        controls.addWidget(self.start_label)
        controls.addWidget(self.end_label)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.waveform)
        layout.addLayout(controls)

        self.open_button.clicked.connect(self.open_audio_file)
        self.save_session_button.clicked.connect(self.save_session_file)
        self.load_session_button.clicked.connect(self.load_session_file)
        self.export_segments_button.clicked.connect(self.export_segments)
        self.play_button.clicked.connect(self.play)
        self.stop_button.clicked.connect(self.stop)
        self.reset_button.clicked.connect(self.reset_loop)
        self.extend_audio_button.clicked.connect(self.extend_audio)

        self.waveform.loop_region_changed.connect(self._set_loop_region)
        self.waveform.seek_requested.connect(self._seek)

        self._player.playback_position_changed.connect(self.waveform.set_playhead)

        self._audio = np.zeros((0, 1), dtype=np.float32)
        self._sample_rate = 44100
        self._audio_path = None

    def open_audio_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.wav *.flac *.ogg *.aiff *.aif);;All Files (*)",
        )

        if not path:
            return

        self.load_audio(Path(path))

    def load_audio(self, path: Path):
        audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)

        self._audio_path = path
        self._audio = audio
        self._sample_rate = sample_rate

        self._set_audio(audio, sample_rate)

        self._set_loop_region(0, len(audio))

    def _set_audio(self, audio, sample_rate):
        self.waveform.set_audio(audio, sample_rate)
        self._player.set_audio(audio, sample_rate)

    def save_session_file(self):
        if not self._has_audio():
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Loop Session",
            self._default_session_name(),
            "Loop Session (*.loop.json);;JSON Files (*.json)",
        )

        if not path:
            return

        session_path = Path(path)
        loop = self.waveform.loop_region()

        data = {
            "version": 1,
            "source_audio_path": str(self._audio_path) if self._audio_path else None,
            "sample_rate": self._sample_rate,
            "sample_count": int(len(self._audio)),
            "channels": int(self._audio.shape[1]),
            "loop_start_sample": int(loop.start_sample),
            "loop_end_sample": int(loop.end_sample),
        }

        session_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_session_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Loop Session",
            "",
            "Loop Session (*.loop.json);;JSON Files (*.json);;All Files (*)",
        )

        if not path:
            return

        session_path = Path(path)
        data = json.loads(session_path.read_text(encoding="utf-8"))

        audio_path_text = data.get("source_audio_path")
        audio_path = Path(audio_path_text) if audio_path_text else None

        if audio_path is None or not audio_path.exists():
            selected, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Find Source Audio File",
                "",
                "Audio Files (*.wav *.flac *.ogg *.aiff *.aif);;All Files (*)",
            )

            if not selected:
                return

            audio_path = Path(selected)

        self.load_audio(audio_path)

        loop_start = int(data.get("loop_start_sample", 0))
        loop_end = int(data.get("loop_end_sample", len(self._audio)))

        self._set_loop_region(loop_start, loop_end)
        self.waveform.set_loop_region(loop_start, loop_end)

    def extend_audio(self):
        if not self._has_audio():
            return
        half_samples = self._audio.shape[0] // 2
        self._audio = np.pad(self._audio, ((half_samples, half_samples), (0,0)), mode="constant")
        self._set_audio(self._audio, self._sample_rate)

    def export_segments(self):
        if not self._has_audio():
            return

        loop = self.waveform.loop_region()

        if loop.end_sample <= loop.start_sample:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Loop",
                "The loop end marker must be after the loop start marker.",
            )
            return

        start_name, loop_name = self._default_loop_export_names()
        start_path = self._get_export_audio_path("Export Loop Start File", start_name)

        if start_path is None:
            return

        start_audio = self._audio[loop.start_sample:]
        sf.write(start_path, start_audio, self._sample_rate)

        loop_path = self._get_export_audio_path("Export Loop Start File", loop_name)

        if loop_path is None:
            return

        loop_audio = self._audio[loop.start_sample:loop.end_sample]
        sf.write(loop_path, loop_audio, self._sample_rate)


    def play(self):
        self._player.seek_to_start()
        self._player.play()

    def stop(self):
        self._player.stop()

    def reset_loop(self):
        if len(self._audio) == 0:
            return

        self._set_loop_region(0, len(self._audio))
        self.waveform.set_loop_region(0, len(self._audio))

    def _set_loop_region(self, start_sample: int, end_sample: int):
        self._player.set_loop_region(start_sample, end_sample)

        self.start_label.setText(f"Start: {start_sample}")
        self.end_label.setText(f"End: {end_sample}")

    def _seek(self, sample: int):
        self._player.seek(sample)
        self.waveform.set_playhead(sample)

    def _has_audio(self) -> bool:
        if len(self._audio) > 0:
            return True

        QtWidgets.QMessageBox.information(
            self,
            "No Audio Loaded",
            "Load an audio file first.",
        )
        return False

    def _get_export_audio_path(self, title: str, default_name: str):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            title,
            default_name,
            "WAV Files (*.wav);;FLAC Files (*.flac);;OGG Files (*.ogg);;AIFF Files (*.aiff);;All Files (*)",
        )

        if not path:
            return None

        return Path(path)

    def _default_session_name(self) -> str:
        if self._audio_path is None:
            return "loop_session.loop.json"

        return str(self._audio_path.with_suffix(".loop.json"))

    def _default_audio_export_name(self) -> str:
        if self._audio_path is None:
            return "exported_audio.wav"

        return str(self._audio_path.with_name(f"{self._audio_path.stem}_with_loop{self._audio_path.suffix}"))

    def _default_loop_export_names(self) -> tuple[str, str]:
        if self._audio_path is None:
            return "exported_start.wav", "exported_loop.wav"

        start_name = str(self._audio_path.with_stem(f"{self._audio_path.stem}_start"))
        loop_name = str(self._audio_path.with_stem(f"{self._audio_path.stem}_loop"))

        return start_name, loop_name
