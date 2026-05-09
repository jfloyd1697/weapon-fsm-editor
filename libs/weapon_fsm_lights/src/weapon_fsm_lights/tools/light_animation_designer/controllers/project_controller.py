import traceback
from pathlib import Path

from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from .timeline_controller import Window
from weapon_fsm_lights.infrastructure.authored_project_io import (
    load_authored_project,
    load_project_layout,
    save_authored_project,
)


class ProjectController:
    def __init__(self, window: Window) -> None:
        self.window = window

    def connect(self) -> None:
        ui = self.window.ui
        ui.open_button.clicked.connect(self.open_project)
        ui.save_button.clicked.connect(self.save_project)
        ui.save_as_button.clicked.connect(self.save_project_as)
        ui.recent_combo.activated.connect(self.on_recent_project_selected)

    def load_settings(self) -> None:
        window = self.window
        raw_recent = window.settings.value(
            window.SETTINGS_RECENT_PROJECTS,
            [],
            type=list,
        )

        window.recent_project_paths = []

        for item in raw_recent:
            path = Path(str(item)).expanduser().resolve()

            if path.exists() and path not in window.recent_project_paths:
                window.recent_project_paths.append(path)

    def save_settings(self) -> None:
        window = self.window
        window.settings.setValue(
            window.SETTINGS_RECENT_PROJECTS,
            [
                str(path)
                for path in window.recent_project_paths[: window.MAX_RECENT_PROJECTS]
            ],
        )

        if window.project_path is not None:
            window.settings.setValue(
                window.SETTINGS_LAST_PROJECT,
                str(window.project_path),
            )

    def auto_load_last_project(self) -> None:
        window = self.window
        last = window.settings.value(window.SETTINGS_LAST_PROJECT, "", type=str)

        if not last:
            return

        path = Path(last).expanduser().resolve()

        if path.exists():
            self.load_project(path, remember=True, show_errors=False)

    def remember_project_path(self, path: Path) -> None:
        window = self.window
        resolved = path.expanduser().resolve()
        window.recent_project_paths = [
            item for item in window.recent_project_paths if item != resolved
        ]
        window.recent_project_paths.insert(0, resolved)
        window.recent_project_paths = window.recent_project_paths[
            : window.MAX_RECENT_PROJECTS
        ]

        self.save_settings()
        self.refresh_recent_combo()

    def refresh_recent_combo(self) -> None:
        window = self.window
        combo = window.ui.recent_combo

        with QSignalBlocker(combo):
            combo.clear()
            combo.addItem("Recent projects…", "")

            for path in window.recent_project_paths:
                combo.addItem(path.name, str(path))

    def on_recent_project_selected(self, index: int) -> None:
        combo = self.window.ui.recent_combo
        path_text = combo.itemData(index)
        combo.setCurrentIndex(0)

        if path_text:
            self.load_project(path_text)

    def open_project(self) -> None:
        window = self.window
        start_dir = ""

        if window.project_path is not None:
            start_dir = str(window.project_path.parent)
        elif window.recent_project_paths:
            start_dir = str(window.recent_project_paths[0].parent)

        file_name, _ = QFileDialog.getOpenFileName(
            window,
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
        window = self.window

        try:
            window.project_path = Path(path).expanduser().resolve()
            window.project = load_authored_project(window.project_path)
            window.layout_asset = load_project_layout(window.project_path, window.project)
            window.undo_history.clear()

            window.layer_enabled_by_animation.clear()
            window.animation_controller.reload_list()
            window.timeline_controller.refresh()

            if remember:
                self.remember_project_path(window.project_path)

            window.ui.status_label.setText(f"Loaded {window.project_path}")

        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            if show_errors:
                QMessageBox.critical(window, "Load failed", str(exc))
            else:
                window.ui.status_label.setText(f"Last project load failed: {exc}")

    def save_project(self) -> None:
        window = self.window

        if window.project is None:
            return

        if window.project_path is None:
            self.save_project_as()
            return

        try:
            window.animation_controller.apply_controls()
            save_authored_project(window.project_path, window.project)
            self.remember_project_path(window.project_path)
            window.ui.status_label.setText(f"Saved {window.project_path}")

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(window, "Save failed", str(exc))

    def save_project_as(self) -> None:
        window = self.window

        if window.project is None:
            return

        file_name, _ = QFileDialog.getSaveFileName(
            window,
            "Save light animation project",
            str(window.project_path or Path("light_animation_project.yaml")),
            "YAML files (*.yaml *.yml)",
        )

        if not file_name:
            return

        window.project_path = Path(file_name).expanduser().resolve()
        self.save_project()
