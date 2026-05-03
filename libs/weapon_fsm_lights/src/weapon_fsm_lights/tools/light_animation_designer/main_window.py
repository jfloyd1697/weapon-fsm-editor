import traceback
from copy import deepcopy
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings, QSignalBlocker
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_lights.domain.animation_layers import (
    LightLayerDef,
    SolidLayerDef,
)
from weapon_fsm_lights.domain.animation_project import (
    LightAnimationDef,
    LightAnimationMode,
    LightAnimationProject,
)
from weapon_fsm_lights.domain.compiler import compile_animation
from weapon_fsm_lights.infrastructure.authored_project_io import (
    load_authored_project,
    load_project_layout,
    save_authored_project,
)
from weapon_fsm_lights.presentation.layer_properties_panel import LayerPropertiesPanel
from weapon_fsm_lights.presentation.led_canvas_widget import LedCanvasWidget
from weapon_fsm_lights.presentation.light_animation_player import LightAnimationPlayer
from weapon_fsm_lights.presentation.light_player_controls import LightPlayerControls


class LightAnimationDesignerWindow(QMainWindow):
    SETTINGS_ORGANIZATION = "WeaponFSM"
    SETTINGS_APPLICATION = "LightAnimationDesigner"
    SETTINGS_LAST_PROJECT = "last_project_path"
    SETTINGS_RECENT_PROJECTS = "recent_project_paths"
    MAX_RECENT_PROJECTS = 10

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Light Animation Designer")
        self.resize(1200, 760)

        self._settings = QSettings(
            self.SETTINGS_ORGANIZATION,
            self.SETTINGS_APPLICATION,
        )
        self._recent_project_paths: list[Path] = []
        self._project_path: Path | None = None
        self._project: LightAnimationProject | None = None
        self._layout_asset = None
        self._selected_animation: str | None = None
        self._selected_layer_index: int | None = None
        self._updating_controls = False
        self._updating_lists = False
        self._layer_enabled_by_animation: dict[str, list[bool]] = {}

        self.animation_list = QListWidget()
        self.layer_list = QListWidget()

        self.canvas = LedCanvasWidget(self)
        self.player = LightAnimationPlayer(self)
        self.player.frame_changed.connect(self.canvas.set_frame)
        self.player_controls = LightPlayerControls(self.player, self)

        self.status_label = QLabel("Open an authored light animation YAML project.")
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label.setWordWrap(True)

        self._build_menu_buttons()
        self._build_animation_controls()
        self._build_layer_controls()
        self._build_layout()
        self._connect_signals()
        self._load_settings()
        self._refresh_recent_combo()
        self._auto_load_last_project()

    def _build_menu_buttons(self) -> None:
        self.open_button = QPushButton("Open")
        self.save_button = QPushButton("Save")
        self.save_as_button = QPushButton("Save As")
        self.recompile_button = QPushButton("Recompile Preview")

        self.recent_combo = QComboBox()
        self.recent_combo.setMinimumWidth(320)
        self.recent_combo.addItem("Recent projects…", "")

    def _build_animation_controls(self) -> None:
        self.add_animation_button = QPushButton("Add")
        self.duplicate_animation_button = QPushButton("Duplicate")
        self.delete_animation_button = QPushButton("Delete")

        self.animation_name = QLabel("")
        self.animation_name_edit = QComboBox()
        self.animation_name_edit.setEditable(True)

        self.animation_mode = QComboBox()
        self.animation_mode.addItems([item.value for item in LightAnimationMode])

        self.animation_duration_ms = QSpinBox()
        self.animation_duration_ms.setRange(1, 10 * 60 * 1000)
        self.animation_duration_ms.setValue(1000)

        self.animation_frame_ms = QSpinBox()
        self.animation_frame_ms.setRange(1, 1000)
        self.animation_frame_ms.setValue(33)

    def _build_layer_controls(self) -> None:
        self.add_layer_button = QPushButton("Add Layer")
        self.duplicate_layer_button = QPushButton("Duplicate")
        self.delete_layer_button = QPushButton("Delete")
        self.move_layer_up_button = QPushButton("Up")
        self.move_layer_down_button = QPushButton("Down")
        self.enable_all_layers_button = QPushButton("All Layers")
        self.only_selected_layer_button = QPushButton("Only Selected")

        self.layer_properties = LayerPropertiesPanel(parent=self)

    def _build_layout(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        top = QHBoxLayout()
        top.addWidget(self.open_button)
        top.addWidget(self.save_button)
        top.addWidget(self.save_as_button)
        top.addWidget(self.recompile_button)
        top.addWidget(QLabel("Recent"))
        top.addWidget(self.recent_combo)
        top.addStretch(1)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        left_layout.addWidget(QLabel("Animations"))
        left_layout.addWidget(self.animation_list, 1)

        animation_buttons = QHBoxLayout()
        animation_buttons.addWidget(self.add_animation_button)
        animation_buttons.addWidget(self.duplicate_animation_button)
        animation_buttons.addWidget(self.delete_animation_button)
        left_layout.addLayout(animation_buttons)

        left_layout.addWidget(self._animation_group())

        left_layout.addWidget(QLabel("Layers (checked layers are included in preview)"))
        left_layout.addWidget(self.layer_list, 1)

        layer_buttons = QHBoxLayout()
        layer_buttons.addWidget(self.add_layer_button)
        layer_buttons.addWidget(self.duplicate_layer_button)
        layer_buttons.addWidget(self.delete_layer_button)
        layer_buttons.addWidget(self.move_layer_up_button)
        layer_buttons.addWidget(self.move_layer_down_button)
        left_layout.addLayout(layer_buttons)

        layer_test_buttons = QHBoxLayout()
        layer_test_buttons.addWidget(self.enable_all_layers_button)
        layer_test_buttons.addWidget(self.only_selected_layer_button)
        left_layout.addLayout(layer_test_buttons)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.addWidget(self.canvas, 1)
        center_layout.addWidget(self.player_controls)
        center_layout.addWidget(self.status_label)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.layer_properties)
        right_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        layout = QVBoxLayout(root)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)

    def _animation_group(self) -> QWidget:
        group = QWidget()
        layout = QVBoxLayout(group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name"))
        name_row.addWidget(self.animation_name_edit)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode"))
        mode_row.addWidget(self.animation_mode)

        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel("Duration ms"))
        duration_row.addWidget(self.animation_duration_ms)

        frame_row = QHBoxLayout()
        frame_row.addWidget(QLabel("Frame ms"))
        frame_row.addWidget(self.animation_frame_ms)

        layout.addLayout(name_row)
        layout.addLayout(mode_row)
        layout.addLayout(duration_row)
        layout.addLayout(frame_row)

        return group

    def _connect_signals(self) -> None:
        self.open_button.clicked.connect(self.open_project)
        self.save_button.clicked.connect(self.save_project)
        self.save_as_button.clicked.connect(self.save_project_as)
        self.recompile_button.clicked.connect(self.recompile_preview)
        self.recent_combo.activated.connect(self._on_recent_project_selected)

        self.animation_list.currentItemChanged.connect(self._on_animation_selected)
        self.layer_list.currentRowChanged.connect(self._on_layer_selected)
        self.layer_list.itemChanged.connect(self._on_layer_item_changed)

        self.add_animation_button.clicked.connect(self.add_animation)
        self.duplicate_animation_button.clicked.connect(self.duplicate_animation)
        self.delete_animation_button.clicked.connect(self.delete_animation)

        self.add_layer_button.clicked.connect(self.add_layer)
        self.duplicate_layer_button.clicked.connect(self.duplicate_layer)
        self.delete_layer_button.clicked.connect(self.delete_layer)
        self.move_layer_up_button.clicked.connect(lambda: self.move_layer(-1))
        self.move_layer_down_button.clicked.connect(lambda: self.move_layer(1))
        self.enable_all_layers_button.clicked.connect(self.enable_all_layers)
        self.only_selected_layer_button.clicked.connect(self.only_selected_layer)

        self.animation_name_edit.lineEdit().editingFinished.connect(
            self._apply_animation_controls
        )
        self.animation_mode.currentTextChanged.connect(self._apply_animation_controls)
        self.animation_duration_ms.valueChanged.connect(self._apply_animation_controls)
        self.animation_frame_ms.valueChanged.connect(self._apply_animation_controls)

        self.layer_properties.layer_changed.connect(self._on_layer_properties_changed)

    def _load_settings(self) -> None:
        raw_recent = self._settings.value(
            self.SETTINGS_RECENT_PROJECTS,
            [],
            type=list,
        )

        self._recent_project_paths = []

        for item in raw_recent:
            path = Path(str(item)).expanduser().resolve()

            if path.exists() and path not in self._recent_project_paths:
                self._recent_project_paths.append(path)

    def _save_settings(self) -> None:
        self._settings.setValue(
            self.SETTINGS_RECENT_PROJECTS,
            [
                str(path)
                for path in self._recent_project_paths[: self.MAX_RECENT_PROJECTS]
            ],
        )

        if self._project_path is not None:
            self._settings.setValue(
                self.SETTINGS_LAST_PROJECT,
                str(self._project_path),
            )

    def _auto_load_last_project(self) -> None:
        last = self._settings.value(self.SETTINGS_LAST_PROJECT, "", type=str)

        if not last:
            return

        path = Path(last).expanduser().resolve()

        if path.exists():
            self.load_project(path, remember=True, show_errors=False)

    def _remember_project_path(self, path: Path) -> None:
        resolved = path.expanduser().resolve()

        self._recent_project_paths = [
            item
            for item in self._recent_project_paths
            if item != resolved
        ]
        self._recent_project_paths.insert(0, resolved)
        self._recent_project_paths = self._recent_project_paths[: self.MAX_RECENT_PROJECTS]

        self._save_settings()
        self._refresh_recent_combo()

    def _refresh_recent_combo(self) -> None:
        with QSignalBlocker(self.recent_combo):
            self.recent_combo.clear()
            self.recent_combo.addItem("Recent projects…", "")

            for path in self._recent_project_paths:
                self.recent_combo.addItem(path.name, str(path))

    def _on_recent_project_selected(self, index: int) -> None:
        path_text = self.recent_combo.itemData(index)
        self.recent_combo.setCurrentIndex(0)

        if path_text:
            self.load_project(path_text)

    def open_project(self) -> None:
        start_dir = ""

        if self._project_path is not None:
            start_dir = str(self._project_path.parent)
        elif self._recent_project_paths:
            start_dir = str(self._recent_project_paths[0].parent)

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open light animation project",
            start_dir,
            "YAML files (*.yaml *.yml)",
        )

        if not file_name:
            return

        self.load_project(file_name)

    def load_project(
        self,
        path: str | Path,
        *,
        remember: bool = True,
        show_errors: bool = True,
    ) -> None:
        try:
            self._project_path = Path(path).expanduser().resolve()
            self._project = load_authored_project(self._project_path)
            self._layout_asset = load_project_layout(self._project_path, self._project)

            self._layer_enabled_by_animation.clear()
            self._reload_animation_list()

            if remember:
                self._remember_project_path(self._project_path)

            self.status_label.setText(f"Loaded {self._project_path}")

        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            if show_errors:
                QMessageBox.critical(self, "Load failed", str(exc))
            else:
                self.status_label.setText(f"Last project load failed: {exc}")

    def save_project(self) -> None:
        if self._project is None:
            return

        if self._project_path is None:
            self.save_project_as()
            return

        try:
            self._apply_animation_controls()
            save_authored_project(self._project_path, self._project)
            self._remember_project_path(self._project_path)
            self.status_label.setText(f"Saved {self._project_path}")

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", str(exc))

    def save_project_as(self) -> None:
        if self._project is None:
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save light animation project",
            str(self._project_path or Path("light_animation_project.yaml")),
            "YAML files (*.yaml *.yml)",
        )

        if not file_name:
            return

        self._project_path = Path(file_name).expanduser().resolve()
        self.save_project()

    def _reload_animation_list(self) -> None:
        with QSignalBlocker(self.animation_list):
            self.animation_list.clear()
            self.layer_list.clear()

            if self._project is None:
                return

            for name, animation in self._project.animations.items():
                item = QListWidgetItem(name)
                item.setIcon(self._icon_for_animation(animation))
                self.animation_list.addItem(item)

        if self.animation_list.count() > 0:
            self.animation_list.setCurrentRow(0)
            current = self.animation_list.currentItem()
            self._on_animation_selected(current)

    def _on_animation_selected(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None = None,
    ) -> None:
        if self._project is None or current is None:
            return

        self._selected_animation = current.text()
        self._selected_layer_index = None

        self._load_animation_controls()
        self._reload_layer_list()
        self.recompile_preview(autoplay=False)

    def _reload_layer_list(self) -> None:
        animation = self._current_animation()

        with QSignalBlocker(self.layer_list):
            self.layer_list.clear()

            if animation is None:
                self.layer_properties.clear_layer()
                return

            enabled = self._layer_enabled_for_animation(animation)

            for index, layer in enumerate(animation.layers):
                item = QListWidgetItem(f"{layer.name} ({layer.type})")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked
                    if enabled[index]
                    else Qt.CheckState.Unchecked
                )
                item.setIcon(self._icon_for_color(layer.color))
                self.layer_list.addItem(item)

        if self.layer_list.count() > 0:
            self.layer_list.setCurrentRow(0)
        else:
            self.layer_properties.clear_layer()

    def _reload_layer_list_preserve_selection(self) -> None:
        row = self._selected_layer_index or 0

        self._updating_lists = True
        self._reload_layer_list()

        if self.layer_list.count() > 0:
            row = min(row, self.layer_list.count() - 1)
            self.layer_list.setCurrentRow(row)

        self._updating_lists = False

    def _on_layer_selected(self, row: int) -> None:
        self._selected_layer_index = row if row >= 0 else None
        self._load_layer_controls()

    def _on_layer_item_changed(self, item: QListWidgetItem) -> None:
        if self._updating_controls or self._updating_lists:
            return

        animation = self._current_animation()

        if animation is None or self._selected_animation is None:
            return

        states = [
            item.checkState() == Qt.CheckState.Checked
            for index in range(self.layer_list.count()) if (item := self.layer_list.item(index)) is not None
        ]

        self._layer_enabled_by_animation[self._selected_animation] = states
        self.recompile_preview(autoplay=self.player.is_playing)

    def _current_animation(self) -> LightAnimationDef | None:
        if self._project is None or self._selected_animation is None:
            return None

        return self._project.animations.get(self._selected_animation)

    def _current_layer(self) -> LightLayerDef | None:
        animation = self._current_animation()

        if animation is None or self._selected_layer_index is None:
            return None

        if self._selected_layer_index < 0:
            return None

        if self._selected_layer_index >= len(animation.layers):
            return None

        return animation.layers[self._selected_layer_index]

    def _layer_enabled_for_animation(self, animation: LightAnimationDef) -> list[bool]:
        if self._selected_animation is None:
            return [True] * len(animation.layers)

        existing = list(
            self._layer_enabled_by_animation.get(self._selected_animation, [])
        )

        if len(existing) < len(animation.layers):
            existing.extend([True] * (len(animation.layers) - len(existing)))

        if len(existing) > len(animation.layers):
            existing = existing[: len(animation.layers)]

        self._layer_enabled_by_animation[self._selected_animation] = existing

        return existing

    def _enabled_layer_indexes(self, animation: LightAnimationDef) -> list[int]:
        enabled = self._layer_enabled_for_animation(animation)

        return [
            index
            for index, is_enabled in enumerate(enabled)
            if is_enabled
        ]

    def _preview_animation(self, animation: LightAnimationDef) -> LightAnimationDef:
        enabled_indexes = set(self._enabled_layer_indexes(animation))

        return LightAnimationDef(
            name=animation.name,
            frame_duration_ms=animation.frame_duration_ms,
            duration_ms=animation.duration_ms,
            mode=animation.mode,
            layers=[
                layer
                for index, layer in enumerate(animation.layers)
                if index in enabled_indexes
            ],
        )

    def _load_animation_controls(self) -> None:
        animation = self._current_animation()

        if animation is None:
            return

        self._updating_controls = True

        try:
            with QSignalBlocker(self.animation_name_edit):
                self.animation_name_edit.clear()
                self.animation_name_edit.addItem(animation.name)
                self.animation_name_edit.setCurrentText(animation.name)

            self.animation_mode.setCurrentText(animation.mode.value)
            self.animation_duration_ms.setValue(animation.duration_ms)
            self.animation_frame_ms.setValue(animation.frame_duration_ms)

        finally:
            self._updating_controls = False

    def _load_layer_controls(self) -> None:
        self.layer_properties.set_layer(self.layer_list.currentRow(), self._current_layer())

    def _apply_animation_controls(self) -> None:
        if self._updating_controls:
            return

        animation = self._current_animation()

        if animation is None:
            return

        old_name = self._selected_animation
        new_name = self.animation_name_edit.currentText().strip() or animation.name

        animation.name = new_name
        animation.mode = LightAnimationMode(self.animation_mode.currentText())
        animation.duration_ms = self.animation_duration_ms.value()
        animation.frame_duration_ms = self.animation_frame_ms.value()

        if (
            self._project is not None
            and old_name is not None
            and animation.name != old_name
        ):
            old_enabled = self._layer_enabled_by_animation.pop(old_name, None)
            self._project.animations.pop(old_name)
            self._project.animations[animation.name] = animation
            self._selected_animation = animation.name

            if old_enabled is not None:
                self._layer_enabled_by_animation[animation.name] = old_enabled

            self._reload_animation_list()
            self._select_animation_name(animation.name)

        self._refresh_current_animation_icon()
        self.recompile_preview(autoplay=self.player.is_playing)

    def _on_layer_properties_changed(self, row, updated_layer: LightLayerDef) -> None:
        animation = self._current_animation()

        if animation is None or self._selected_layer_index is None:
            return

        if not (0 <= self._selected_layer_index < len(animation.layers)):
            return

        animation.layers[self._selected_layer_index] = updated_layer

        self._update_row(row, updated_layer)

        # self._reload_layer_list_preserve_selection()
        self._refresh_current_animation_icon()
        self.recompile_preview(autoplay=self.player.is_playing)

    def recompile_preview(self, autoplay: bool | None = None) -> None:
        if self._layout_asset is None:
            return

        animation = self._current_animation()

        if animation is None:
            return

        try:
            was_playing = self.player.is_playing if autoplay is None else autoplay
            preview_animation = self._preview_animation(animation)

            compiled = compile_animation(
                layout=self._layout_asset,
                animation=preview_animation,
            )

            self.canvas.play_sequence(
                compiled,
                sequence_name=animation.name,
                mode=animation.mode.value,
            )
            self.player.set_asset(
                compiled,
                sequence_name=animation.name,
                mode=animation.mode.value,
                autoplay=was_playing,
            )

            enabled_count = len(preview_animation.layers)
            total_count = len(animation.layers)

            self.status_label.setText(
                f"Preview: {animation.name} "
                f"({len(compiled.frames)} frames, "
                f"{enabled_count}/{total_count} layers enabled)"
            )

        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Compile failed: {exc}")

    def add_animation(self) -> None:
        if self._project is None:
            self._project = LightAnimationProject(
                layout={"path": "layouts/cpx_ring.json"},
                animations={},
            )

        base = "new_animation"
        name = self._unique_animation_name(base)

        self._project.animations[name] = LightAnimationDef(
            name=name,
            layers=[
                SolidLayerDef(
                    name="solid",
                    intensity=0.4,
                )
            ],
        )

        self._layer_enabled_by_animation[name] = [True]
        self._reload_animation_list()
        self._select_animation_name(name)

    def duplicate_animation(self) -> None:
        animation = self._current_animation()

        if self._project is None or animation is None:
            return

        name = self._unique_animation_name(f"{animation.name}_copy")
        copied = deepcopy(animation)
        copied.name = name

        self._project.animations[name] = copied
        self._layer_enabled_by_animation[name] = list(
            self._layer_enabled_for_animation(animation)
        )

        self._reload_animation_list()
        self._select_animation_name(name)

    def delete_animation(self) -> None:
        if self._project is None or self._selected_animation is None:
            return

        self._project.animations.pop(self._selected_animation, None)
        self._layer_enabled_by_animation.pop(self._selected_animation, None)
        self._selected_animation = None

        self._reload_animation_list()

    def _select_animation_name(self, name: str) -> None:
        for row in range(self.animation_list.count()):
            if self.animation_list.item(row).text() == name:
                self.animation_list.setCurrentRow(row)
                return

    def _unique_animation_name(self, base: str) -> str:
        existing = set(self._project.animations if self._project is not None else {})

        if base not in existing:
            return base

        index = 2

        while f"{base}_{index}" in existing:
            index += 1

        return f"{base}_{index}"

    def add_layer(self) -> None:
        animation = self._current_animation()

        if animation is None:
            return

        animation.layers.append(
            SolidLayerDef(
                name="New Layer",
                intensity=0.4,
            )
        )

        enabled = self._layer_enabled_for_animation(animation)
        enabled.append(True)

        self._reload_layer_list()
        self.layer_list.setCurrentRow(len(animation.layers) - 1)
        self._refresh_current_animation_icon()
        self.recompile_preview(autoplay=self.player.is_playing)

    def duplicate_layer(self) -> None:
        animation = self._current_animation()
        layer = self._current_layer()

        if animation is None or layer is None:
            return

        copied = deepcopy(layer)
        copied.name = f"{layer.name} copy"

        animation.layers.append(copied)

        enabled = self._layer_enabled_for_animation(animation)
        enabled.append(True)

        self._reload_layer_list()
        self.layer_list.setCurrentRow(len(animation.layers) - 1)
        self._refresh_current_animation_icon()
        self.recompile_preview(autoplay=self.player.is_playing)

    def delete_layer(self) -> None:
        animation = self._current_animation()

        if animation is None or self._selected_layer_index is None:
            return

        if 0 <= self._selected_layer_index < len(animation.layers):
            animation.layers.pop(self._selected_layer_index)

            enabled = self._layer_enabled_for_animation(animation)

            if self._selected_layer_index < len(enabled):
                enabled.pop(self._selected_layer_index)

        self._reload_layer_list()
        self._refresh_current_animation_icon()
        self.recompile_preview(autoplay=self.player.is_playing)

    def move_layer(self, direction: int) -> None:
        animation = self._current_animation()

        if animation is None or self._selected_layer_index is None:
            return

        old = self._selected_layer_index
        new = old + direction

        if new < 0 or new >= len(animation.layers):
            return

        animation.layers[old], animation.layers[new] = (
            animation.layers[new],
            animation.layers[old],
        )

        enabled = self._layer_enabled_for_animation(animation)
        enabled[old], enabled[new] = enabled[new], enabled[old]

        self._reload_layer_list()
        self.layer_list.setCurrentRow(new)
        self._refresh_current_animation_icon()
        self.recompile_preview(autoplay=self.player.is_playing)

    def enable_all_layers(self) -> None:
        animation = self._current_animation()

        if animation is None or self._selected_animation is None:
            return

        self._layer_enabled_by_animation[self._selected_animation] = [
            True
        ] * len(animation.layers)

        self._reload_layer_list_preserve_selection()
        self.recompile_preview(autoplay=self.player.is_playing)

    def only_selected_layer(self) -> None:
        animation = self._current_animation()

        if (
            animation is None
            or self._selected_animation is None
            or self._selected_layer_index is None
        ):
            return

        self._layer_enabled_by_animation[self._selected_animation] = [
            index == self._selected_layer_index
            for index in range(len(animation.layers))
        ]

        self._reload_layer_list_preserve_selection()
        self.recompile_preview(autoplay=self.player.is_playing)

    def _icon_for_animation(self, animation: LightAnimationDef) -> QIcon:
        return self._icon_for_color(self._animation_icon_color(animation))

    def _animation_icon_color(self, animation: LightAnimationDef) -> str:
        best_color = "#202020"
        best_intensity = -1.0

        for layer in animation.layers:
            if layer.intensity >= best_intensity:
                best_color = layer.color
                best_intensity = layer.intensity

        return best_color

    def _icon_for_color(self, color_text: str) -> QIcon:
        color = QColor(color_text if color_text else "#202020")

        if not color.isValid():
            color = QColor("#202020")

        pixmap = QPixmap(16, 16)
        pixmap.fill(color)

        return QIcon(pixmap)

    def _refresh_current_animation_icon(self) -> None:
        if self._selected_animation is None:
            return

        animation = self._current_animation()

        if animation is None:
            return

        for row in range(self.animation_list.count()):
            item = self.animation_list.item(row)

            if item.text() == self._selected_animation:
                item.setIcon(self._icon_for_animation(animation))
                break

    def _update_row(self, row, layer):
        # with QSignalBlocker(self.layer_list):
            item = self.layer_list.item(row)
            item.setText(f"{layer.name} ({layer.type})")
            item.setIcon(self._icon_for_color(layer.color))
