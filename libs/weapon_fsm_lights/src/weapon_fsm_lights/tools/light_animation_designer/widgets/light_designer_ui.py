from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_lights.domain.animation_project import LightAnimationMode
from weapon_fsm_lights.presentation.layer_properties_panel import LayerPropertiesPanel
from weapon_fsm_lights.presentation.led_canvas_widget import LedCanvasWidget
from weapon_fsm_lights.presentation.light_animation_player import LightAnimationPlayer
from weapon_fsm_lights.presentation.light_player_controls import LightPlayerControls

from .timeline_widget import TimelineWidget


class LightDesignerUi:
    def __init__(self, window: QMainWindow) -> None:
        self.window = window

        self.animation_list = QListWidget()
        self.layer_list = QListWidget()

        self.canvas = LedCanvasWidget(window)
        self.player = LightAnimationPlayer(window)
        self.player_controls = LightPlayerControls(self.player, window)
        self.timeline = TimelineWidget(window)

        self.layer_properties = LayerPropertiesPanel(parent=window)

        self.status_label = QLabel("Open an authored light animation YAML project.")
        self.status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.status_label.setWordWrap(True)

        self._build_menu_buttons()
        self._build_animation_controls()
        self._build_layer_controls()
        self._build_layout()

    def _build_menu_buttons(self) -> None:
        self.open_button = QPushButton("Open")
        self.save_button = QPushButton("Save")
        self.save_as_button = QPushButton("Save As")
        self.recompile_button = QPushButton("Recompile Preview")
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")

        self.show_canvas_button = QPushButton("Show Canvas")
        self.show_canvas_button.setCheckable(True)
        self.show_canvas_button.setChecked(False)

        self.recent_combo = QComboBox()
        self.recent_combo.setMinimumWidth(320)
        self.recent_combo.addItem("Recent projects…", "")

    def _build_animation_controls(self) -> None:
        self.add_animation_button = QPushButton("Add")
        self.add_preset_button = QPushButton("Add Preset")
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

    def _build_layout(self) -> None:
        root = QWidget(self.window)
        self.window.setCentralWidget(root)

        top = QHBoxLayout()
        top.addWidget(self.open_button)
        top.addWidget(self.save_button)
        top.addWidget(self.save_as_button)
        top.addWidget(self.recompile_button)
        top.addWidget(self.undo_button)
        top.addWidget(self.redo_button)
        top.addWidget(self.show_canvas_button)
        top.addWidget(QLabel("Recent"))
        top.addWidget(self.recent_combo)
        top.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        layout = QVBoxLayout(root)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)

    def _build_left_panel(self) -> QWidget:
        left = QWidget()
        left_layout = QVBoxLayout(left)

        left_layout.addWidget(QLabel("Animations"))
        left_layout.addWidget(self.animation_list, 1)

        animation_buttons = QHBoxLayout()
        animation_buttons.addWidget(self.add_animation_button)
        animation_buttons.addWidget(self.add_preset_button)
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

        return left

    def _build_center_panel(self) -> QWidget:
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.addWidget(self.canvas, 1)
        center_layout.addWidget(self.timeline)
        center_layout.addWidget(self.player_controls)
        center_layout.addWidget(self.status_label)
        return center

    def _build_right_panel(self) -> QWidget:
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.layer_properties)
        right_layout.addStretch(1)
        return right

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
