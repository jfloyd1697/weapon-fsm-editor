from dataclasses import replace
import json
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_lights import LightSequenceAsset, load_light_sequence


class LedCanvasWidget(QWidget):
    led_moved = pyqtSignal(str, float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._sequence_name: str | None = None
        self._mode: str = "one_shot"
        self._asset: LightSequenceAsset | None = None
        self._frame_index: int = 0
        self._current_frame_leds: dict[str, tuple[str, float]] = {}
        self._background_pixmap: QPixmap | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)
        self._edit_mode = False
        self._drag_led_id: str | None = None

    @property
    def asset(self) -> LightSequenceAsset | None:
        return self._asset

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        self.update()

    def set_asset(self, asset: LightSequenceAsset, *, sequence_name: str = "layout", mode: str = "one_shot") -> None:
        self.play_sequence(asset, sequence_name=sequence_name, mode=mode)

    def play_sequence(self, asset: LightSequenceAsset, *, sequence_name: str, mode: str) -> None:
        self._timer.stop()
        self._sequence_name = sequence_name
        self._mode = mode
        self._asset = asset
        self._frame_index = 0
        self._current_frame_leds = {}
        self._background_pixmap = None
        if asset.background_path is not None and asset.background_path.exists():
            self._background_pixmap = QPixmap(str(asset.background_path))
        if asset.frames:
            self._apply_frame(0)
        self.update()

    def stop_sequence(self) -> None:
        self._timer.stop()
        self._sequence_name = None
        self._mode = "one_shot"
        self._asset = None
        self._frame_index = 0
        self._current_frame_leds = {}
        self._background_pixmap = None
        self._drag_led_id = None
        self.update()

    def _apply_frame(self, index: int) -> None:
        if self._asset is None or not self._asset.frames:
            return
        frame = self._asset.frames[index]
        self._frame_index = index
        self._current_frame_leds = dict(frame.leds)
        if len(self._asset.frames) > 1:
            self._timer.start(max(1, frame.duration_ms))
        else:
            self._timer.stop()
        self.update()

    def _advance_frame(self) -> None:
        if self._asset is None or not self._asset.frames:
            self._timer.stop()
            return

        next_index = self._frame_index + 1
        if next_index >= len(self._asset.frames):
            if self._mode == "loop":
                next_index = 0
            else:
                self._timer.stop()
                return

        self._apply_frame(next_index)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._edit_mode or self._asset is None or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        hit = self._hit_test(event.position())
        if hit is not None:
            self._drag_led_id = hit
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._edit_mode or self._asset is None or self._drag_led_id is None:
            return super().mouseMoveEvent(event)
        x, y = self._widget_to_asset(event.position())
        self._move_led(self._drag_led_id, x, y)
        self.led_moved.emit(self._drag_led_id, x, y)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_led_id = None
        super().mouseReleaseEvent(event)

    def _move_led(self, led_id: str, x: float, y: float) -> None:
        if self._asset is None:
            return
        x = max(0.0, min(self._asset.width, x))
        y = max(0.0, min(self._asset.height, y))
        updated = []
        for led in self._asset.leds:
            updated.append(replace(led, x=x, y=y) if led.id == led_id else led)
        self._asset = replace(self._asset, leds=tuple(updated))
        self.update()

    def _layout_rect(self) -> QRectF:
        if self._asset is None:
            return QRectF()
        content_rect = QRectF(self.rect()).adjusted(12, 12, -12, -12)
        scale = min(content_rect.width() / self._asset.width, content_rect.height() / self._asset.height)
        draw_width = self._asset.width * scale
        draw_height = self._asset.height * scale
        origin_x = content_rect.x() + (content_rect.width() - draw_width) / 2.0
        origin_y = content_rect.y() + (content_rect.height() - draw_height) / 2.0
        return QRectF(origin_x, origin_y, draw_width, draw_height)

    def _widget_to_asset(self, point: QPointF) -> tuple[float, float]:
        asset = self._asset
        if asset is None:
            return 0.0, 0.0
        draw_rect = self._layout_rect()
        if draw_rect.width() <= 0 or draw_rect.height() <= 0:
            return 0.0, 0.0
        u = (point.x() - draw_rect.x()) / draw_rect.width()
        v = (point.y() - draw_rect.y()) / draw_rect.height()
        return u * asset.width, v * asset.height

    def _asset_to_widget(self, x: float, y: float) -> tuple[float, float, float]:
        asset = self._asset
        if asset is None:
            return 0.0, 0.0, 1.0
        draw_rect = self._layout_rect()
        scale = min(draw_rect.width() / asset.width, draw_rect.height() / asset.height)
        return draw_rect.x() + x * scale, draw_rect.y() + y * scale, scale

    def _hit_test(self, point: QPointF) -> str | None:
        asset = self._asset
        if asset is None:
            return None
        for led in reversed(asset.leds):
            cx, cy, scale = self._asset_to_widget(led.x, led.y)
            radius = max(6.0, led.radius * scale)
            dx = point.x() - cx
            dy = point.y() - cy
            if (dx * dx) + (dy * dy) <= (radius * radius):
                return led.id
        return None

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().window())

        asset = self._asset
        if asset is None:
            self._paint_empty(painter)
            return

        draw_rect = self._layout_rect()
        if draw_rect.width() <= 0 or draw_rect.height() <= 0:
            return

        painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawRoundedRect(draw_rect, 8, 8)

        if self._background_pixmap is not None and not self._background_pixmap.isNull():
            painter.drawPixmap(draw_rect.toRect(), self._background_pixmap)

        for led in asset.leds:
            state = self._current_frame_leds.get(led.id)
            if state is None:
                color = QColor("#3a3a3a")
                color.setAlpha(180)
                glow = QColor("#2a2a2a")
            else:
                color = QColor(state[0])
                color.setAlpha(max(60, int(255 * state[1])))
                glow = QColor(color)
                glow.setAlpha(max(40, int(180 * state[1])))

            cx, cy, scale = self._asset_to_widget(led.x, led.y)
            radius = max(3.0, led.radius * scale)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(cx, cy), radius * 1.8, radius * 1.8)

            pen_color = QColor("#00d0ff") if self._edit_mode else QColor("#0f0f0f")
            painter.setPen(QPen(pen_color, 1.5 if self._edit_mode else 1.0))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(cx, cy), radius, radius)

            label = led.label or led.id
            painter.setPen(QPen(QColor("#d8d8d8"), 1))
            painter.drawText(
                QRectF(cx + radius + 3, cy - 10, 100, 20),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

    def _paint_empty(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#888888"), 1))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(12, 12, -12, -12), 8, 8)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No light sequence active")


class LedPreviewPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_asset_path: Path | None = None
        self._example_layout_path: Path | None = None
        self.title_label = QLabel("LED Preview / Layout Editor")
        self.canvas = LedCanvasWidget(self)
        self.status_label = QLabel("Idle")
        self.status_label.setWordWrap(True)
        self.edit_checkbox = QCheckBox("Edit layout")
        self.edit_checkbox.toggled.connect(self.canvas.set_edit_mode)
        self.load_button = QPushButton("Load Layout")
        self.load_button.clicked.connect(self._load_layout)
        self.save_button = QPushButton("Save Layout")
        self.save_button.clicked.connect(self._save_layout)
        self.example_button = QPushButton("Load Example")
        self.example_button.clicked.connect(self._load_example_layout)
        self.example_button.setEnabled(False)
        self.canvas.led_moved.connect(self._on_led_moved)

        controls = QHBoxLayout()
        controls.addWidget(self.edit_checkbox)
        controls.addWidget(self.load_button)
        controls.addWidget(self.save_button)
        controls.addWidget(self.example_button)
        controls.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.title_label)
        layout.addLayout(controls)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.status_label)


    def set_example_layout_path(self, path: str | Path | None) -> None:
        self._example_layout_path = Path(path).expanduser().resolve() if path else None
        self.example_button.setEnabled(self._example_layout_path is not None and self._example_layout_path.exists())

    def play_sequence(
        self,
        asset: LightSequenceAsset,
        *,
        sequence_name: str,
        mode: str,
        asset_path: Path | None = None,
    ) -> None:
        self._current_asset_path = asset_path
        self.canvas.play_sequence(asset, sequence_name=sequence_name, mode=mode)
        location = f" ({asset_path.name})" if asset_path is not None else ""
        self.status_label.setText(f"Playing: {sequence_name}{location} [{mode}]")

    def stop_sequence(self) -> None:
        self._current_asset_path = None
        self.canvas.stop_sequence()
        self.status_label.setText("Idle")

    def set_status_text(self, message: str) -> None:
        self.status_label.setText(message)

    def load_layout_path(self, path: str | Path) -> None:
        asset = load_light_sequence(path)
        self._current_asset_path = Path(path).expanduser().resolve()
        self.canvas.set_asset(asset, sequence_name=self._current_asset_path.stem, mode="one_shot")
        self.status_label.setText(f"Loaded layout: {self._current_asset_path.name}")

    def _load_layout(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load LED layout or light sequence",
            str(self._current_asset_path.parent) if self._current_asset_path is not None else "",
            "Layout/Sequence (*.json *.yaml *.yml)",
        )
        if file_name:
            try:
                self.load_layout_path(file_name)
            except Exception as exc:  # noqa: BLE001
                self.set_status_text(f"Load failed: {exc}")


    def _load_example_layout(self) -> None:
        if self._example_layout_path is None:
            self.set_status_text("No example layout configured")
            return
        try:
            self.load_layout_path(self._example_layout_path)
        except Exception as exc:  # noqa: BLE001
            self.set_status_text(f"Example load failed: {exc}")

    def _save_layout(self) -> None:
        asset = self.canvas.asset
        if asset is None:
            self.set_status_text("Nothing to save")
            return
        initial = str((self._current_asset_path or Path("layout.json")).with_suffix(".json"))
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save LED layout JSON",
            initial,
            "JSON files (*.json)",
        )
        if not file_name:
            return
        payload = {
            "name": Path(file_name).stem,
            "coordinate_space": "normalized_2d" if asset.width == 1.0 and asset.height == 1.0 else "canvas_2d",
            "leds": [],
        }
        for order, led in enumerate(asset.leds):
            entry = {
                "index": led.index if led.index is not None else order,
                "u": led.x / asset.width if asset.width else 0.0,
                "v": led.y / asset.height if asset.height else 0.0,
                "led_radius": led.radius / max(asset.width, asset.height, 1.0),
            }
            if led.label:
                entry["label"] = led.label
            if led.id != str(entry["index"]):
                entry["id"] = led.id
            payload["leds"].append(entry)
        Path(file_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.set_status_text(f"Saved layout: {Path(file_name).name}")

    def _on_led_moved(self, led_id: str, x: float, y: float) -> None:
        asset = self.canvas.asset
        if asset is None:
            return
        if asset.width == 1.0 and asset.height == 1.0:
            self.status_label.setText(f"Moved LED {led_id} to u={x:.4f}, v={y:.4f}")
        else:
            self.status_label.setText(f"Moved LED {led_id} to x={x:.1f}, y={y:.1f}")
