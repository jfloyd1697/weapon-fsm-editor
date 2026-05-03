import argparse
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_lights.presentation.led_canvas_widget import LedCanvasWidget
from weapon_fsm_lights.presentation.light_animation_player import LightAnimationPlayer
from weapon_fsm_lights.presentation.light_player_controls import LightPlayerControls

from weapon_fsm_lights.tools.lights_preview_gui.multi_sequence_loader import NamedLightAnimation, load_light_animations


class LightsPreviewWindow(QMainWindow):
    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()

        self.setWindowTitle("Weapon FSM Lights Preview")
        self.resize(1100, 720)

        self._current_path: Path | None = None
        self._animations: list[NamedLightAnimation] = []

        self.player = LightAnimationPlayer(self)
        self.canvas = LedCanvasWidget(self)
        self.controls = LightPlayerControls(self.player, self)
        self.animation_list = QListWidget(self)
        self.status_label = QLabel("Load a light YAML to preview animations.")
        self.status_label.setWordWrap(True)

        self.load_button = QPushButton("Load YAML")
        self.reload_button = QPushButton("Reload")
        self.reload_button.setEnabled(False)

        button_row = QHBoxLayout()
        button_row.addWidget(self.load_button)
        button_row.addWidget(self.reload_button)
        button_row.addStretch(1)

        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.addLayout(button_row)
        left_layout.addWidget(QLabel("Animations"))
        left_layout.addWidget(self.animation_list, 1)
        left_layout.addWidget(self.status_label)

        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.canvas, 1)
        right_layout.addWidget(self.controls)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 840])

        self.setCentralWidget(splitter)

        self.load_button.clicked.connect(self._choose_file)
        self.reload_button.clicked.connect(self._reload_current)
        self.animation_list.currentRowChanged.connect(self._select_animation)
        self.player.frame_changed.connect(self.canvas.set_frame)

        if initial_path is not None:
            self.load_file(initial_path)

    def load_file(self, path: str | Path) -> None:
        source_path = Path(path).expanduser().resolve()

        try:
            animations = load_light_animations(source_path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load failed", str(exc))
            self.status_label.setText(f"Load failed: {exc}")
            return

        self._current_path = source_path
        self._animations = animations
        self.reload_button.setEnabled(True)
        self.animation_list.clear()

        for animation in animations:
            item = QListWidgetItem(animation.name)
            item.setToolTip(str(animation.source_path))
            self.animation_list.addItem(item)

        self.status_label.setText(
            f"Loaded {len(animations)} animation(s) from {source_path.name}"
        )

        if animations:
            self.animation_list.setCurrentRow(0)

    def _choose_file(self) -> None:
        start_dir = str(self._current_path.parent) if self._current_path else str(Path.cwd())
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load light animation YAML",
            start_dir,
            "Light files (*.yaml *.yml *.json);;All files (*.*)",
        )
        if file_name:
            self.load_file(file_name)

    def _reload_current(self) -> None:
        if self._current_path is not None:
            selected_name = self._selected_animation_name()
            self.load_file(self._current_path)
            if selected_name is not None:
                self._select_animation_by_name(selected_name)

    def _select_animation(self, row: int) -> None:
        if row < 0 or row >= len(self._animations):
            return

        animation = self._animations[row]
        self.canvas.play_sequence(
            animation.asset,
            sequence_name=animation.name,
            mode="loop",
        )
        self.player.set_asset(
            animation.asset,
            sequence_name=animation.name,
            mode="loop",
            autoplay=True,
        )
        self.status_label.setText(
            f"Previewing '{animation.name}' | "
            f"{len(animation.asset.leds)} LEDs | "
            f"{len(animation.asset.frames)} frame(s)"
        )

    def _selected_animation_name(self) -> str | None:
        row = self.animation_list.currentRow()
        if row < 0 or row >= len(self._animations):
            return None
        return self._animations[row].name

    def _select_animation_by_name(self, name: str) -> None:
        for index, animation in enumerate(self._animations):
            if animation.name == name:
                self.animation_list.setCurrentRow(index)
                return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview weapon FSM light animations")
    parser.add_argument("path", nargs="?", help="Optional YAML/JSON light sequence path")
    args = parser.parse_args(argv)

    app = QApplication(sys.argv[:1])
    window = LightsPreviewWindow(Path(args.path) if args.path else None)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
