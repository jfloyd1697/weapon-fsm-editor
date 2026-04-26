from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_core.domain.model import WeaponConfig
from weapon_fsm_audio.infrastructure.runtime.qt_audio_backend import QtAudioBackend


class AudioLibraryBrowser(QWidget):
    def __init__(self, audio_backend: QtAudioBackend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._audio_backend = audio_backend
        self._weapon: WeaponConfig | None = None

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["one_shot", "loop"])
        self._interrupt_combo = QComboBox()
        self._interrupt_combo.addItems(["interrupt", "schedule", "ignore"])

        self._clips_list = QListWidget()
        self._effects_list = QListWidget()
        self._details = QTextEdit()
        self._details.setReadOnly(True)

        self._build_ui()
        self._clips_list.currentItemChanged.connect(self._refresh_details)
        self._effects_list.currentItemChanged.connect(self._refresh_details)

    def set_weapon(self, weapon: WeaponConfig | None) -> None:
        self._weapon = weapon
        self._clips_list.clear()
        self._effects_list.clear()
        self._details.clear()

        if weapon is None:
            return

        for clip_name in sorted(weapon.clips):
            self._clips_list.addItem(QListWidgetItem(clip_name))

        for effect_name in sorted(weapon.audio_effects):
            self._effects_list.addItem(QListWidgetItem(effect_name))

        if self._clips_list.count() > 0:
            self._clips_list.setCurrentRow(0)
        if self._effects_list.count() > 0:
            self._effects_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        clip_group = QGroupBox("Clips")
        clip_layout = QVBoxLayout(clip_group)
        clip_layout.addWidget(self._clips_list)

        effect_group = QGroupBox("Effects")
        effect_layout = QVBoxLayout(effect_group)
        effect_layout.addWidget(self._effects_list)

        lists_row = QHBoxLayout()
        lists_row.addWidget(clip_group)
        lists_row.addWidget(effect_group)
        root.addLayout(lists_row)

        form = QFormLayout()
        form.addRow("Preview mode", self._mode_combo)
        form.addRow("Interrupt", self._interrupt_combo)
        root.addLayout(form)

        buttons = QHBoxLayout()
        play_clip_button = QPushButton("Play Clip")
        play_clip_button.clicked.connect(self._play_selected_clip)
        play_effect_button = QPushButton("Play Effect")
        play_effect_button.clicked.connect(self._play_selected_effect)
        spam_button = QPushButton("Retrigger x3")
        spam_button.clicked.connect(self._spam_selected)
        stop_button = QPushButton("Stop All")
        stop_button.clicked.connect(self._audio_backend.stop_audio)

        buttons.addWidget(play_clip_button)
        buttons.addWidget(play_effect_button)
        buttons.addWidget(spam_button)
        buttons.addWidget(stop_button)
        root.addLayout(buttons)

        root.addWidget(QLabel("Selection details"))
        root.addWidget(self._details)

    def _refresh_details(self) -> None:
        parts: list[str] = []
        clip_name = self._current_clip_name()
        effect_name = self._current_effect_name()

        if self._weapon is not None and clip_name is not None:
            clip = self._weapon.clips[clip_name]
            parts.append(f"Clip: {clip_name}")
            parts.append(f"  path: {clip.path}")
            parts.append(f"  resolved: {self._weapon.resolve_asset_path(clip.path)}")
            parts.append(f"  preload: {clip.preload}")

        if self._weapon is not None and effect_name is not None:
            effect = self._weapon.audio_effects[effect_name]
            parts.append("")
            parts.append(f"Effect: {effect_name}")
            parts.append(f"  mode: {effect.resolved_mode}")
            parts.append(f"  interrupt: {effect.interrupt}")
            parts.append(f"  clips: {', '.join(effect.clips)}")
            parts.append(f"  gain: {effect.gain}")

        self._details.setPlainText("\n".join(parts).strip())

    def _play_selected_clip(self) -> None:
        if self._weapon is None:
            return
        clip_name = self._current_clip_name()
        if clip_name is None:
            return

        clip = self._weapon.clips.get(clip_name)
        if clip is None:
            return

        self._audio_backend.play_audio(
            clip=clip_name,
            path=self._weapon.resolve_asset_path(clip.path),
            mode=self._mode_combo.currentText(),
            interrupt=self._interrupt_combo.currentText(),
        )

    def _play_selected_effect(self) -> None:
        if self._weapon is None:
            return
        effect_name = self._current_effect_name()
        if effect_name is None:
            return

        effect = self._weapon.audio_effects.get(effect_name)
        if effect is None or not effect.clips:
            return

        clip_name = effect.clips[0]
        clip = self._weapon.clips.get(clip_name)
        if clip is None:
            return

        mode = effect.resolved_mode
        if mode == "random":
            mode = "one_shot"

        self._audio_backend.play_audio(
            clip=clip_name,
            path=self._weapon.resolve_asset_path(clip.path),
            mode=mode,
            interrupt=effect.interrupt,
        )

    def _spam_selected(self) -> None:
        for _ in range(3):
            if self._effects_list.currentItem() is not None:
                self._play_selected_effect()
            else:
                self._play_selected_clip()

    def _current_clip_name(self) -> str | None:
        item = self._clips_list.currentItem()
        if item is None:
            return None
        return item.text()

    def _current_effect_name(self) -> str | None:
        item = self._effects_list.currentItem()
        if item is None:
            return None
        return item.text()
