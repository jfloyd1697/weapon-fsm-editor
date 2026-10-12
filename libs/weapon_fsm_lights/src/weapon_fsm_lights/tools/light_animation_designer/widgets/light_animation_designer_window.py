from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget

from weapon_fsm_lights.domain.animation_project import LightAnimationProject

from ..controllers.preset_controller import PresetController
from ..controllers import (
    LayerController,
    AnimationController,
    PreviewController,
    ProjectController,
    TimelineController,
    UndoController,
)

from ..model import (
    LightDesignerContext,
    LightDesignerState,
    SnapshotUndoHistory,
)

from .light_designer_ui import LightDesignerUi


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

        self.settings = QSettings(
            self.SETTINGS_ORGANIZATION,
            self.SETTINGS_APPLICATION,
        )

        self.recent_project_paths: list[Path] = []
        self.project_path: Path | None = None
        self.project: LightAnimationProject | None = None
        self.layout_asset = None
        self.selected_animation: str | None = None
        self.selected_layer_index: int | None = None
        self.updating_controls = False
        self.updating_lists = False
        self.layer_enabled_by_animation: dict[str, list[bool]] = {}

        self.ui = LightDesignerUi(self)
        self.context = LightDesignerContext(self)

        self.undo_history = SnapshotUndoHistory[LightDesignerState](
            parent=self,
            capture_state=self.context.capture_state,
            restore_state=self.restore_state,
        )

        self.preview_controller = PreviewController(self)
        self.timeline_controller = TimelineController(self)
        self.animation_controller = AnimationController(self)
        self.layer_controller = LayerController(self)
        self.project_controller = ProjectController(self)
        self.preset_controller = PresetController(self)
        self.undo_controller = UndoController(self)

        self.ui.player.frame_changed.connect(self.ui.canvas.set_frame)

        self._connect_controllers()

        self.project_controller.load_settings()
        self.project_controller.refresh_recent_combo()
        self.project_controller.auto_load_last_project()
        self.timeline_controller.refresh()

    def _connect_controllers(self) -> None:
        self.preview_controller.connect()
        self.timeline_controller.connect()
        self.animation_controller.connect()
        self.layer_controller.connect()
        self.project_controller.connect()
        self.preset_controller.connect()
        self.undo_controller.connect()

        self.undo_controller.install_event_filter(QApplication.instance())

    def restore_state(self, state: LightDesignerState) -> None:
        was_updating_controls = self.updating_controls
        was_updating_lists = self.updating_lists

        self.updating_controls = True
        self.updating_lists = True

        try:
            self.context.restore_state(state)

            if self.project is not None and self.project_path is not None:
                from weapon_fsm_lights.infrastructure.authored_project_io import (
                    load_project_layout,
                )

                self.layout_asset = load_project_layout(
                    self.project_path,
                    self.project,
                )

            self.animation_controller.reload_list()

            if self.selected_animation is not None:
                self.animation_controller.select_name(self.selected_animation)

            if self.selected_layer_index is not None and self.ui.layer_list.count() > 0:
                row = min(self.selected_layer_index, self.ui.layer_list.count() - 1)
                self.ui.layer_list.setCurrentRow(row)

        finally:
            self.updating_controls = was_updating_controls
            self.updating_lists = was_updating_lists

        self.animation_controller.load_controls()
        self.layer_controller.load_controls()
        self.timeline_controller.refresh()
        self.preview_controller.recompile(autoplay=self.ui.player.is_playing)

    def record_undo(self, text: str, before: LightDesignerState) -> None:
        self.undo_history.record(text, before)

    def load_project(self, file: str):
        self.project_controller.load_project(file)
