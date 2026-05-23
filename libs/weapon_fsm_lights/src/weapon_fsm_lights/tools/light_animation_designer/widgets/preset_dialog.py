from __future__ import annotations

from copy import deepcopy
import logging
import traceback

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_lights.domain.animation_presets import (
    AnimationPreset,
    presets_by_category,
)
from weapon_fsm_lights.domain.animation_project import LightAnimationMode
from weapon_fsm_lights.domain.animation_transforms import (
    invert_animation,
    reverse_animation,
)
from weapon_fsm_lights.domain.compiler import compile_animation
from weapon_fsm_lights.presentation.led_canvas_widget import LedCanvasWidget


LOGGER = logging.getLogger(__name__)


class PresetDialog(QDialog):
    ONCE_PREVIEW_EXTRA_MS = 750

    def __init__(
        self,
        *,
        layout_asset=None,
        parent: QWidget | None = None,
    ) -> None:
        LOGGER.debug(
            "PresetDialog.__init__ start layout_asset=%r parent=%r",
            layout_asset,
            parent,
        )
        super().__init__(parent)

        self.setWindowTitle("Add Animation Preset")
        self.resize(960, 560)

        self._layout_asset = layout_asset
        self._presets_by_category = presets_by_category()
        self._selected_preset: AnimationPreset | None = None

        self._preview_frames = []
        self._preview_frame_index = 0
        self._preview_generation = 0
        self._closing = False

        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._advance_preview_frame)

        self.category_list = QListWidget()
        self.preset_list = QListWidget()

        self.description = QTextEdit()
        self.description.setReadOnly(True)

        self.reverse_animation_checkbox = QCheckBox("Reverse timing")
        self.invert_animation_checkbox = QCheckBox("Invert light / dark")

        LOGGER.debug("PresetDialog creating preview canvas")
        self.preview_canvas = LedCanvasWidget(self)
        LOGGER.debug("PresetDialog preview canvas created")

        self.preview_status = QLabel("")
        self.preview_status.setWordWrap(True)
        self._set_info_message("")

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._build_layout()
        self._load_categories()
        self._connect_signals()

        LOGGER.debug("PresetDialog.__init__ complete")

    def selected_preset(self) -> AnimationPreset | None:
        return self._selected_preset

    def reverse_animation_enabled(self) -> bool:
        return self.reverse_animation_checkbox.isChecked()

    def invert_animation_enabled(self) -> bool:
        return self.invert_animation_checkbox.isChecked()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        LOGGER.debug("PresetDialog.closeEvent")
        self._closing = True
        self._stop_preview()
        super().closeEvent(event)

    def reject(self) -> None:
        LOGGER.debug("PresetDialog.reject")
        self._closing = True
        self._stop_preview()
        super().reject()

    def accept(self) -> None:
        LOGGER.debug("PresetDialog.accept selected=%r", self._selected_preset)
        self._closing = True
        self._stop_preview()
        super().accept()

    def _build_layout(self) -> None:
        LOGGER.debug("PresetDialog._build_layout start")

        root = QVBoxLayout(self)
        main = QHBoxLayout()

        picker_column = QVBoxLayout()
        lists = QHBoxLayout()

        category_column = QVBoxLayout()
        category_column.addWidget(QLabel("Category"))
        category_column.addWidget(self.category_list)

        preset_column = QVBoxLayout()
        preset_column.addWidget(QLabel("Preset"))
        preset_column.addWidget(self.preset_list)

        lists.addLayout(category_column, 1)
        lists.addLayout(preset_column, 2)

        picker_column.addLayout(lists, 2)
        picker_column.addWidget(QLabel("Description"))
        picker_column.addWidget(self.description, 1)

        options_row = QHBoxLayout()
        options_row.addWidget(self.reverse_animation_checkbox)
        options_row.addWidget(self.invert_animation_checkbox)
        options_row.addStretch(1)
        picker_column.addLayout(options_row)

        preview_column = QVBoxLayout()
        preview_column.addWidget(QLabel("Preview"))
        preview_column.addWidget(self.preview_canvas, 1)
        preview_column.addWidget(self.preview_status)

        main.addLayout(picker_column, 2)
        main.addLayout(preview_column, 3)

        root.addLayout(main, 1)
        root.addWidget(self.buttons)

        LOGGER.debug("PresetDialog._build_layout complete")

    def _connect_signals(self) -> None:
        LOGGER.debug("PresetDialog._connect_signals")

        self.category_list.currentItemChanged.connect(self._on_category_selected)
        self.preset_list.currentItemChanged.connect(self._on_preset_selected)

        self.reverse_animation_checkbox.toggled.connect(self._refresh_current_preview)
        self.invert_animation_checkbox.toggled.connect(self._refresh_current_preview)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def _load_categories(self) -> None:
        categories = sorted(self._presets_by_category)
        LOGGER.debug("PresetDialog._load_categories categories=%s", categories)

        self.category_list.clear()

        for category in categories:
            self.category_list.addItem(category)

        if self.category_list.count() > 0:
            LOGGER.debug("PresetDialog selecting first category")
            self.category_list.setCurrentRow(0)

    def _on_category_selected(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None = None,
    ) -> None:
        del previous

        category = current.text() if current is not None else None
        LOGGER.debug("PresetDialog._on_category_selected category=%r", category)

        self.preset_list.clear()
        self.description.clear()
        self._selected_preset = None
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._clear_preview()

        if current is None:
            return

        presets = self._presets_by_category.get(category, [])
        LOGGER.debug(
            "PresetDialog loading %d presets for category=%r",
            len(presets),
            category,
        )

        for preset in presets:
            item = QListWidgetItem(preset.name)
            item.setData(Qt.ItemDataRole.UserRole, preset)
            self.preset_list.addItem(item)

        if self.preset_list.count() > 0:
            LOGGER.debug("PresetDialog selecting first preset in category=%r", category)
            self.preset_list.setCurrentRow(0)

    def _on_preset_selected(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None = None,
    ) -> None:
        del previous

        LOGGER.debug(
            "PresetDialog._on_preset_selected current=%r closing=%s",
            current.text() if current is not None else None,
            self._closing,
        )

        if self._closing:
            return

        if current is None:
            self._selected_preset = None
            self.description.clear()
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self._clear_preview()
            return

        preset = current.data(Qt.ItemDataRole.UserRole)
        self._selected_preset = preset

        LOGGER.debug(
            "PresetDialog selected preset name=%s category=%s duration=%s mode=%s layers=%s",
            preset.name,
            preset.category,
            preset.animation.duration_ms,
            preset.animation.mode.value,
            len(preset.animation.layers),
        )

        self.description.setPlainText(
            f"{preset.name}\n\n"
            f"Category: {preset.category}\n\n"
            f"{preset.description}\n\n"
            f"Duration: {preset.animation.duration_ms} ms\n"
            f"Frame: {preset.animation.frame_duration_ms} ms\n"
            f"Mode: {preset.animation.mode.value}\n"
            f"Layers: {len(preset.animation.layers)}"
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

        self._preview_preset(preset)

    def _refresh_current_preview(self) -> None:
        if self._selected_preset is None:
            return

        self._preview_preset(self._selected_preset)

    def _preview_preset(self, preset: AnimationPreset) -> None:
        self._preview_generation += 1
        generation = self._preview_generation

        LOGGER.debug(
            "PresetDialog._preview_preset start generation=%s preset=%s reverse=%s invert=%s",
            generation,
            preset.name,
            self.reverse_animation_enabled(),
            self.invert_animation_enabled(),
        )

        if self._layout_asset is None:
            LOGGER.warning("PresetDialog preview requested without layout asset")
            self._clear_preview()
            self._set_warning_message(
                "Open a project with a layout to preview presets."
            )
            return

        try:
            preview_animation = self._make_looping_preview_animation(preset)

            LOGGER.debug(
                "PresetDialog compiling preview generation=%s name=%s duration=%s mode=%s layers=%s",
                generation,
                preview_animation.name,
                preview_animation.duration_ms,
                preview_animation.mode.value,
                len(preview_animation.layers),
            )
            compiled = compile_animation(
                layout=self._layout_asset,
                animation=preview_animation,
            )

            LOGGER.debug(
                "PresetDialog compile complete generation=%s frames=%s leds=%s",
                generation,
                len(compiled.frames),
                len(compiled.leds),
            )

            self._stop_preview()

            if hasattr(self.preview_canvas, "set_canvas_animation"):
                self.preview_canvas.set_canvas_animation(preview_animation)

            self.preview_canvas.play_sequence(
                compiled,
                sequence_name=preview_animation.name,
                mode=LightAnimationMode.LOOP.value,
            )

            self._preview_frames = list(compiled.frames)
            self._preview_frame_index = 0

            if self._preview_frames:
                self._set_preview_frame(self._preview_frames[0])

            frame_ms = max(1, int(preview_animation.frame_duration_ms))
            self.preview_timer.start(frame_ms)

            if preset.animation.mode == LightAnimationMode.ONCE:
                self._set_info_message(
                    "Preview looping ONCE preset with extra reset time. "
                    "The inserted preset keeps its original ONCE mode."
                )
            else:
                self._set_info_message("Preview looping preset.")

        except Exception as exc:  # noqa: BLE001
            traceback_text = self._print_traceback_here(
                f"PresetDialog preview failed generation={generation} preset={preset.name}"
            )
            self._clear_preview()
            self._set_error_message(
                f"Preset preview failed: {exc}\n\n{traceback_text}"
            )

    def _make_looping_preview_animation(self, preset: AnimationPreset):
        LOGGER.debug(
            "PresetDialog._make_looping_preview_animation preset=%s mode=%s duration=%s reverse=%s invert=%s",
            preset.name,
            preset.animation.mode.value,
            preset.animation.duration_ms,
            self.reverse_animation_enabled(),
            self.invert_animation_enabled(),
        )

        preview = deepcopy(preset.animation)

        if self.reverse_animation_enabled():
            preview = reverse_animation(preview)

        if self.invert_animation_enabled():
            preview = invert_animation(preview)

        if preview.mode == LightAnimationMode.ONCE:
            preview.duration_ms = max(
                preview.duration_ms + self.ONCE_PREVIEW_EXTRA_MS,
                preview.duration_ms * 2,
            )

        preview.mode = LightAnimationMode.LOOP

        LOGGER.debug(
            "PresetDialog preview animation mode=%s duration=%s",
            preview.mode.value,
            preview.duration_ms,
        )

        return preview

    def _advance_preview_frame(self) -> None:
        if self._closing:
            LOGGER.debug("PresetDialog timer ignored because dialog is closing")
            return

        if not self._preview_frames:
            LOGGER.debug("PresetDialog timer tick with no frames")
            return

        try:
            frame_index = self._preview_frame_index
            frame = self._preview_frames[frame_index]

            LOGGER.debug(
                "PresetDialog timer set_frame index=%s/%s",
                frame_index,
                len(self._preview_frames),
            )

            self._set_preview_frame(frame)

            self._preview_frame_index += 1

            if self._preview_frame_index >= len(self._preview_frames):
                self._preview_frame_index = 0

        except Exception as exc:  # noqa: BLE001
            traceback_text = self._print_traceback_here(
                "PresetDialog timer advance failed"
            )
            self._stop_preview()
            self._set_error_message(
                f"Preset preview stopped after an error: {exc}\n\n{traceback_text}"
            )

    def _set_preview_frame(self, frame) -> None:  # noqa: ANN001
        LOGGER.debug(
            "PresetDialog._set_preview_frame frame_index=%s frame=%r",
            self._preview_frame_index,
            frame,
        )
        self.preview_canvas.set_frame(self._preview_frame_index, frame)

    def _stop_preview(self) -> None:
        LOGGER.debug(
            "PresetDialog._stop_preview active=%s frames=%s index=%s",
            self.preview_timer.isActive(),
            len(self._preview_frames),
            self._preview_frame_index,
        )

        self.preview_timer.stop()
        self._preview_frames = []
        self._preview_frame_index = 0

    def _clear_preview(self) -> None:
        LOGGER.debug("PresetDialog._clear_preview")
        self._stop_preview()
        self._set_info_message("")

        try:
            self.preview_canvas.update()

        except Exception as exc:  # noqa: BLE001
            traceback_text = self._print_traceback_here(
                "PresetDialog failed while clearing preview canvas"
            )
            self._set_error_message(
                f"Preset preview clear failed: {exc}\n\n{traceback_text}"
            )

    def _print_traceback_here(self, message: str) -> str:
        traceback_text = traceback.format_exc()

        LOGGER.error("%s\n%s", message, traceback_text)
        print(f"{message}\n{traceback_text}")

        return traceback_text

    def _set_info_message(self, text: str) -> None:
        self.preview_status.setStyleSheet("color: palette(window-text);")
        self.preview_status.setText(text)

    def _set_warning_message(self, text: str) -> None:
        self.preview_status.setStyleSheet("color: #ff5f5f;")
        self.preview_status.setText(text)

    def _set_error_message(self, text: str) -> None:
        self.preview_status.setStyleSheet("color: #ff5f5f;")
        self.preview_status.setText(text)