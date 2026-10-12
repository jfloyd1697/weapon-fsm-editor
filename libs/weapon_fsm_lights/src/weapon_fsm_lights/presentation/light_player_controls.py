from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_lights.presentation.light_animation_player import (
    LightAnimationPlayer,
    LightPlaybackState,
)


class LightPlayerControls(QWidget):
    def __init__(self, player: LightAnimationPlayer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._player = player

        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.previous_button = QPushButton("Prev")
        self.next_button = QPushButton("Next")

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["once", "loop"])

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.05, 4.0)
        self.speed_spin.setSingleStep(0.05)
        self.speed_spin.setValue(1.0)

        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setRange(0, 0)

        self.status_label = QLabel("No sequence")
        self.status_label.setMinimumWidth(240)

        row = QHBoxLayout()
        row.addWidget(self.play_button)
        row.addWidget(self.pause_button)
        row.addWidget(self.stop_button)
        row.addWidget(self.previous_button)
        row.addWidget(self.next_button)
        row.addWidget(QLabel("Mode"))
        row.addWidget(self.mode_combo)
        row.addWidget(QLabel("Speed"))
        row.addWidget(self.speed_spin)
        row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.frame_slider)
        layout.addWidget(self.status_label)

        self.play_button.clicked.connect(self._player.play)
        self.pause_button.clicked.connect(self._player.pause)
        self.stop_button.clicked.connect(self._player.stop)
        self.previous_button.clicked.connect(self._player.step_previous)
        self.next_button.clicked.connect(self._player.step_next)
        self.mode_combo.currentTextChanged.connect(self._player.set_mode)
        self.speed_spin.valueChanged.connect(self._player.set_speed)
        self.frame_slider.sliderMoved.connect(self._player.seek_frame)
        self._player.playback_state_changed.connect(self._on_state_changed)

    def _on_state_changed(self, state: LightPlaybackState) -> None:
        max_frame = max(0, state.frame_count - 1)
        if self.frame_slider.maximum() != max_frame:
            self.frame_slider.setRange(0, max_frame)
        if not self.frame_slider.isSliderDown():
            self.frame_slider.setValue(state.frame_index)
        if self.mode_combo.currentText() != state.mode:
            self.mode_combo.setCurrentText(state.mode)
        if abs(self.speed_spin.value() - state.speed) > 0.0001:
            self.speed_spin.setValue(state.speed)
        self.status_label.setText(
            f"{state.sequence_name or 'No sequence'} | "
            f"frame {state.frame_index + 1}/{state.frame_count} | "
            f"{state.elapsed_frame_ms}/{state.frame_duration_ms} ms | "
            f"{state.mode} | {state.speed:.2f}x"
        )
