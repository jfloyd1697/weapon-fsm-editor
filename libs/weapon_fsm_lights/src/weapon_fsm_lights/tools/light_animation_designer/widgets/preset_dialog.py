from __future__ import annotations

from copy import deepcopy
import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
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

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def _load_categories(self) -> None:
        LOGGER.debug(
            "PresetDialog._load_categories categories=%s",
            sorted(self._presets_by_category),
        )

        self.category_list.clear()

        for category in sorted(self._presets_by_category):
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

    def _preview_preset(self, preset: AnimationPreset) -> None:
        self._preview_generation += 1
        generation = self._preview_generation

        LOGGER.debug(
            "PresetDialog._preview_preset start generation=%s preset=%s",
            generation,
            preset.name,
        )

        if self._layout_asset is None:
            LOGGER.warning("PresetDialog preview requested without layout asset")
            self._clear_preview()
            self._set_warning_message(
                "Open a project with a layout to preview presets."
            )
            return

        try:
            LOGGER.debug("PresetDialog make looping preview generation=%s", generation)
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
                LOGGER.debug(
                    "PresetDialog set_canvas_animation generation=%s",
                    generation,
                )
                self.preview_canvas.set_canvas_animation(preview_animation)

            LOGGER.debug("PresetDialog play_sequence generation=%s", generation)
            self.preview_canvas.play_sequence(
                compiled,
                sequence_name=preview_animation.name,
                mode=LightAnimationMode.LOOP.value,
            )

            self._preview_frames = list(compiled.frames)
            self._preview_frame_index = 0

            if self._preview_frames:
                LOGGER.debug("PresetDialog set first frame generation=%s", generation)
                self.preview_canvas.set_frame(self._preview_frames[0])

            frame_ms = max(1, int(preview_animation.frame_duration_ms))
            LOGGER.debug(
                "PresetDialog starting timer generation=%s frame_ms=%s frame_count=%s",
                generation,
                frame_ms,
                len(self._preview_frames),
            )
            self.preview_timer.start(frame_ms)

            if preset.animation.mode == LightAnimationMode.ONCE:
                self._set_info_message(
                    "Preview looping ONCE preset with extra reset time. "
                    "The inserted preset keeps its original ONCE mode."
                )
            else:
                self._set_info_message("Preview looping preset.")

            LOGGER.debug("PresetDialog._preview_preset complete generation=%s", generation)

        except Exception as exc:  # noqa: BLE001
            LOGGER.exception(
                "PresetDialog preview failed generation=%s preset=%s",
                generation,
                preset.name,
            )
            self._clear_preview()
            self._set_error_message(f"Preset preview failed: {exc}")

    def _make_looping_preview_animation(self, preset: AnimationPreset):
        LOGGER.debug(
            "PresetDialog._make_looping_preview_animation preset=%s mode=%s duration=%s",
            preset.name,
            preset.animation.mode.value,
            preset.animation.duration_ms,
        )

        preview = deepcopy(preset.animation)

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

            self.preview_canvas.set_frame(frame)

            self._preview_frame_index += 1

            if self._preview_frame_index >= len(self._preview_frames):
                self._preview_frame_index = 0

        except Exception:  # noqa: BLE001
            LOGGER.exception("PresetDialog timer advance failed")
            self._stop_preview()
            self._set_error_message("Preset preview stopped after an error.")

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
            if hasattr(self.preview_canvas, "set_frame"):
                LOGGER.debug("PresetDialog clearing preview canvas frame")
                self.preview_canvas.set_frame({})
            else:
                LOGGER.debug("PresetDialog updating preview canvas")
                self.preview_canvas.update()

        except Exception:  # noqa: BLE001
            LOGGER.exception("PresetDialog failed while clearing preview canvas")
            self.preview_canvas.update()

    def _set_info_message(self, text: str) -> None:
        self.preview_status.setStyleSheet("color: palette(window-text);")
        self.preview_status.setText(text)

    def _set_warning_message(self, text: str) -> None:
        self.preview_status.setStyleSheet("color: #ff5f5f;")
        self.preview_status.setText(text)

    def _set_error_message(self, text: str) -> None:
        self.preview_status.setStyleSheet("color: #ff5f5f;")
        self.preview_status.setText(text)