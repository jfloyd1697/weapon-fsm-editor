from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_core.domain.model import ClipDef, WeaponConfig


class AudioLibraryBrowser(QWidget):
    def __init__(self, audio_backend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._audio_backend = audio_backend
        self._weapon: WeaponConfig | None = None
        self._spam_timer = QTimer(self)
        self._spam_timer.timeout.connect(self._trigger_spam_play)

        self.title_label = QLabel("Audio Library / Preview")
        self.clip_list = QListWidget(self)
        self.clip_list.currentItemChanged.connect(self._on_selection_changed)

        self.path_label = QLabel("No clip selected")
        self.path_label.setWordWrap(True)
        self.duration_hint_label = QLabel("Select a clip to preview it.")
        self.duration_hint_label.setWordWrap(True)

        self.interrupt_combo = QComboBox(self)
        self.interrupt_combo.addItems(["interrupt", "schedule", "ignore"])

        self.spam_interval_spin = QSpinBox(self)
        self.spam_interval_spin.setRange(20, 5000)
        self.spam_interval_spin.setValue(120)
        self.spam_interval_spin.setSuffix(" ms")

        self.play_once_button = QPushButton("Play Once", self)
        self.play_once_button.clicked.connect(self._play_once)
        self.play_loop_button = QPushButton("Play Loop", self)
        self.play_loop_button.clicked.connect(self._play_loop)
        self.stop_button = QPushButton("Stop Clip", self)
        self.stop_button.clicked.connect(self._stop_selected_clip)
        self.stop_all_button = QPushButton("Stop All", self)
        self.stop_all_button.clicked.connect(self._audio_backend.stop_audio)
        self.retrigger_button = QPushButton("Retrigger Once", self)
        self.retrigger_button.clicked.connect(self._retrigger_once)
        self.spam_toggle_button = QPushButton("Start Spam Test", self)
        self.spam_toggle_button.clicked.connect(self._toggle_spam_test)

        details_group = QGroupBox("Selected Clip", self)
        details_layout = QFormLayout(details_group)
        details_layout.addRow("Path", self.path_label)
        details_layout.addRow("Notes", self.duration_hint_label)
        details_layout.addRow("Interrupt", self.interrupt_combo)
        details_layout.addRow("Spam interval", self.spam_interval_spin)

        preview_row_1 = QHBoxLayout()
        preview_row_1.addWidget(self.play_once_button)
        preview_row_1.addWidget(self.play_loop_button)
        preview_row_1.addWidget(self.stop_button)

        preview_row_2 = QHBoxLayout()
        preview_row_2.addWidget(self.retrigger_button)
        preview_row_2.addWidget(self.spam_toggle_button)
        preview_row_2.addWidget(self.stop_all_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.clip_list, stretch=1)
        layout.addWidget(details_group)
        layout.addLayout(preview_row_1)
        layout.addLayout(preview_row_2)

        self._update_button_state()

    def set_weapon(self, weapon: WeaponConfig | None) -> None:
        self._weapon = weapon
        self._spam_timer.stop()
        self.spam_toggle_button.setText("Start Spam Test")
        self.clip_list.clear()
        if weapon is None:
            self.path_label.setText("No clip selected")
            self.duration_hint_label.setText("Load a weapon profile to browse its clips.")
            self._update_button_state()
            return

        for clip_name in sorted(weapon.clips):
            item = QListWidgetItem(clip_name)
            item.setData(256, clip_name)
            self.clip_list.addItem(item)

        if self.clip_list.count() > 0:
            self.clip_list.setCurrentRow(0)
        else:
            self.path_label.setText("No clip selected")
            self.duration_hint_label.setText("This weapon does not define any clips.")
        self._update_button_state()

    def _selected_clip(self) -> tuple[str, ClipDef, str] | None:
        item = self.clip_list.currentItem()
        if item is None or self._weapon is None:
            return None
        clip_name = str(item.data(256) or item.text())
        clip_def = self._weapon.clips.get(clip_name)
        if clip_def is None:
            return None
        path = self._weapon.resolve_asset_path(clip_def.path)
        return clip_name, clip_def, path

    def _on_selection_changed(self) -> None:
        selected = self._selected_clip()
        if selected is None:
            self.path_label.setText("No clip selected")
            self.duration_hint_label.setText("Select a clip to preview it.")
            self._update_button_state()
            return

        clip_name, clip_def, resolved_path = selected
        exists = Path(resolved_path).exists()
        preload_text = "preload" if clip_def.preload else "stream on demand"
        path_state = resolved_path if exists else f"{resolved_path} (missing)"
        self.path_label.setText(path_state)
        self.duration_hint_label.setText(
            f"Clip '{clip_name}' is set to {preload_text}. Use the interrupt mode to test restart, queue, and ignore behavior."
        )
        self._update_button_state()

    def _play_once(self) -> None:
        self._play_selected(mode="one_shot")

    def _play_loop(self) -> None:
        self._play_selected(mode="loop")

    def _retrigger_once(self) -> None:
        self._play_selected(mode="one_shot")
        self._play_selected(mode="one_shot")

    def _toggle_spam_test(self) -> None:
        if self._spam_timer.isActive():
            self._spam_timer.stop()
            self.spam_toggle_button.setText("Start Spam Test")
            return
        selected = self._selected_clip()
        if selected is None:
            return
        self._spam_timer.start(self.spam_interval_spin.value())
        self.spam_toggle_button.setText("Stop Spam Test")
        self._trigger_spam_play()

    def _trigger_spam_play(self) -> None:
        if self._selected_clip() is None:
            self._spam_timer.stop()
            self.spam_toggle_button.setText("Start Spam Test")
            return
        self._play_selected(mode="one_shot")

    def _stop_selected_clip(self) -> None:
        selected = self._selected_clip()
        if selected is None:
            return
        clip_name, _, _ = selected
        if hasattr(self._audio_backend, "stop_clip"):
            self._audio_backend.stop_clip(clip_name)
        else:
            self._audio_backend.stop_audio()

    def _play_selected(self, mode: str) -> None:
        selected = self._selected_clip()
        if selected is None:
            return
        clip_name, _, resolved_path = selected
        self._audio_backend.play_audio(
            clip=clip_name,
            path=resolved_path,
            mode=mode,
            interrupt=self.interrupt_combo.currentText(),
        )

    def _update_button_state(self) -> None:
        has_selection = self._selected_clip() is not None
        for button in (
            self.play_once_button,
            self.play_loop_button,
            self.stop_button,
            self.stop_all_button,
            self.retrigger_button,
            self.spam_toggle_button,
        ):
            button.setEnabled(has_selection or button is self.stop_all_button)
