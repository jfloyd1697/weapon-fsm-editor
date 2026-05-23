\
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


@dataclass(frozen=True)
class TimelineLayer:
    name: str
    color: str
    start_ms: int
    duration_ms: int
    enabled: bool = True


@dataclass
class _DragState:
    kind: str
    row: int | None
    mouse_start_ms: int
    original_start_ms: int
    original_duration_ms: int
    original_total_ms: int


class TimelineWidget(QWidget):
    edit_started = pyqtSignal()
    edit_finished = pyqtSignal(str)

    duration_changed = pyqtSignal(int)
    layer_timing_changed = pyqtSignal(int, int, int)
    selected_layer_changed = pyqtSignal(int)

    HANDLE_RADIUS = 6
    MIN_DURATION_MS = 1
    SNAP_MS = 10

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setMinimumHeight(120)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self.setMouseTracking(True)

        self._duration_ms = 1000
        self._layers: list[TimelineLayer] = []
        self._selected_row: int | None = None
        self._playhead_ms = 0
        self._drag: _DragState | None = None
        self._edit_started_for_drag = False

    def set_timeline(
        self,
        *,
        duration_ms: int,
        layers: list[TimelineLayer],
        selected_row: int | None = None,
    ) -> None:
        self._duration_ms = max(self.MIN_DURATION_MS, int(duration_ms))
        self._layers = list(layers)
        self.set_selected_row(selected_row)
        self.updateGeometry()
        self.update()

    def set_selected_row(self, row: int | None) -> None:
        if row is None or not (0 <= row < len(self._layers)):
            self._selected_row = None
        else:
            self._selected_row = row

        self.update()

    def set_playhead_ms(self, time_ms: int) -> None:
        self._playhead_ms = max(0, min(self._duration_ms, int(time_ms)))
        self.update()

    def sizeHint(self) -> QSize:
        height = self._top_margin() + max(1, len(self._layers)) * self._row_height() + 34
        return QSize(600, height)

    def minimumSizeHint(self) -> QSize:
        return QSize(300, 100)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().window())

        self._paint_header(painter)
        self._paint_rows(painter)
        self._paint_total_marker(painter)
        self._paint_playhead(painter)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        hit = self._hit_test(event.position())

        if hit is None:
            self._selected_row = None
            self.update()
            return

        kind, row = hit
        mouse_ms = self._snap_ms(self._x_to_ms(event.position().x()))

        if kind == "total":
            self._drag = _DragState(
                kind=kind,
                row=None,
                mouse_start_ms=mouse_ms,
                original_start_ms=0,
                original_duration_ms=0,
                original_total_ms=self._duration_ms,
            )
            self._begin_drag_edit()
            return

        if row is None or not (0 <= row < len(self._layers)):
            return

        layer = self._layers[row]
        self._selected_row = row
        self.selected_layer_changed.emit(row)

        self._drag = _DragState(
            kind=kind,
            row=row,
            mouse_start_ms=mouse_ms,
            original_start_ms=layer.start_ms,
            original_duration_ms=layer.duration_ms,
            original_total_ms=self._duration_ms,
        )
        self._begin_drag_edit()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is None:
            self._update_cursor(event.position())
            return

        mouse_ms = self._snap_ms(self._x_to_ms(event.position().x()))
        delta_ms = mouse_ms - self._drag.mouse_start_ms

        if self._drag.kind == "total":
            new_duration = max(
                self.MIN_DURATION_MS,
                self._drag.original_total_ms + delta_ms,
            )
            max_layer_end = max(
                (layer.start_ms + layer.duration_ms for layer in self._layers),
                default=self.MIN_DURATION_MS,
            )
            new_duration = max(new_duration, max_layer_end)

            self._duration_ms = new_duration
            self.duration_changed.emit(new_duration)
            self.update()
            return

        if self._drag.row is None:
            return

        row = self._drag.row
        original_start = self._drag.original_start_ms
        original_duration = self._drag.original_duration_ms
        original_end = original_start + original_duration

        if self._drag.kind == "left":
            new_start = max(
                0,
                min(original_end - self.MIN_DURATION_MS, original_start + delta_ms),
            )
            new_duration = original_end - new_start

        elif self._drag.kind == "right":
            new_end = max(
                original_start + self.MIN_DURATION_MS,
                original_end + delta_ms,
            )
            new_end = min(new_end, self._duration_ms)
            new_start = original_start
            new_duration = new_end - new_start

        elif self._drag.kind == "move":
            new_start = max(
                0,
                min(self._duration_ms - original_duration, original_start + delta_ms),
            )
            new_duration = original_duration

        else:
            return

        self._replace_layer_timing(row, new_start, new_duration)
        self.layer_timing_changed.emit(row, new_start, new_duration)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._drag is None:
            return

        kind = self._drag.kind
        self._drag = None

        if self._edit_started_for_drag:
            self._edit_started_for_drag = False
            self.edit_finished.emit(
                "Edit Animation Duration" if kind == "total" else "Edit Layer Timing"
            )

        self.update()

    def leaveEvent(self, event) -> None:  # noqa: ANN001
        if self._drag is None:
            self.unsetCursor()

    def _begin_drag_edit(self) -> None:
        if not self._edit_started_for_drag:
            self._edit_started_for_drag = True
            self.edit_started.emit()

    def _replace_layer_timing(self, row: int, start_ms: int, duration_ms: int) -> None:
        layer = self._layers[row]
        self._layers[row] = TimelineLayer(
            name=layer.name,
            color=layer.color,
            start_ms=max(0, int(start_ms)),
            duration_ms=max(self.MIN_DURATION_MS, int(duration_ms)),
            enabled=layer.enabled,
        )

    def _paint_header(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#8a8a8a"), 1))
        painter.drawText(
            QRectF(0, 0, self._label_width() - 8, self._top_margin()),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "Timeline",
        )

        track = self._track_rect()
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawLine(
            QPointF(track.left(), self._top_margin() - 10),
            QPointF(track.right(), self._top_margin() - 10),
        )

        tick_count = 5
        for index in range(tick_count + 1):
            ratio = index / tick_count
            ms = int(self._duration_ms * ratio)
            x = track.left() + track.width() * ratio

            painter.drawLine(
                QPointF(x, self._top_margin() - 15),
                QPointF(x, self._top_margin() - 5),
            )
            painter.drawText(
                QRectF(x - 40, 2, 80, 18),
                Qt.AlignmentFlag.AlignCenter,
                f"{ms} ms",
            )

    def _paint_rows(self, painter: QPainter) -> None:
        if not self._layers:
            painter.setPen(QPen(QColor("#777777"), 1))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No layers")
            return

        font_metrics = QFontMetrics(painter.font())

        for row, layer in enumerate(self._layers):
            row_rect = self._row_rect(row)
            bar_rect = self._bar_rect(row, layer)

            if row == self._selected_row:
                painter.fillRect(row_rect, QColor(255, 255, 255, 24))

            painter.setPen(QPen(QColor("#333333"), 1))
            painter.drawLine(
                QPointF(row_rect.left(), row_rect.bottom()),
                QPointF(row_rect.right(), row_rect.bottom()),
            )

            label = font_metrics.elidedText(
                layer.name,
                Qt.TextElideMode.ElideRight,
                self._label_width() - 12,
            )
            painter.setPen(QPen(QColor("#cfcfcf"), 1))
            painter.drawText(
                QRectF(4, row_rect.top(), self._label_width() - 10, row_rect.height()),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

            color = QColor(layer.color if layer.color else "#808080")
            if not color.isValid():
                color = QColor("#808080")
            if not layer.enabled:
                color.setAlpha(80)

            painter.setPen(QPen(QColor("#111111"), 1))
            painter.setBrush(color)
            painter.drawRoundedRect(bar_rect, 4, 4)

            painter.setPen(QPen(QColor(self._text_color_for_background(color)), 1))
            painter.drawText(
                bar_rect.adjusted(6, 0, -6, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{layer.start_ms} + {layer.duration_ms}",
            )

            handle_color = QColor("#f0f0f0") if layer.enabled else QColor("#9a9a9a")
            painter.setBrush(handle_color)
            painter.setPen(QPen(QColor("#101010"), 1))
            painter.drawEllipse(QPointF(bar_rect.left(), bar_rect.center().y()), 4, 4)
            painter.drawEllipse(QPointF(bar_rect.right(), bar_rect.center().y()), 4, 4)

    def _paint_total_marker(self, painter: QPainter) -> None:
        x = self._ms_to_x(self._duration_ms)
        top = self._top_margin() - 22
        bottom = self.height() - 8

        painter.setPen(QPen(QColor("#ffcc00"), 2))
        painter.drawLine(QPointF(x, top), QPointF(x, bottom))
        painter.setBrush(QColor("#ffcc00"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(
            QPointF(x, top),
            QPointF(x - 7, top - 9),
            QPointF(x + 7, top - 9),
        )

    def _paint_playhead(self, painter: QPainter) -> None:
        x = self._ms_to_x(self._playhead_ms)
        top = self._top_margin() - 18
        bottom = self.height() - 8

        painter.setPen(QPen(QColor("#00d0ff"), 1))
        painter.drawLine(QPointF(x, top), QPointF(x, bottom))

    def _hit_test(self, point: QPointF) -> tuple[str, int | None] | None:
        total_x = self._ms_to_x(self._duration_ms)

        if abs(point.x() - total_x) <= self.HANDLE_RADIUS + 3:
            return "total", None

        row = self._row_at_y(point.y())
        if row is None:
            return None

        bar_rect = self._bar_rect(row, self._layers[row])
        if not bar_rect.adjusted(-6, -4, 6, 4).contains(point):
            return None

        if abs(point.x() - bar_rect.left()) <= self.HANDLE_RADIUS:
            return "left", row

        if abs(point.x() - bar_rect.right()) <= self.HANDLE_RADIUS:
            return "right", row

        return "move", row

    def _update_cursor(self, point: QPointF) -> None:
        hit = self._hit_test(point)
        if hit is None:
            self.unsetCursor()
            return

        kind, _ = hit
        if kind in {"left", "right", "total"}:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif kind == "move":
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()

    def _row_at_y(self, y: float) -> int | None:
        row = int((y - self._top_margin()) // self._row_height())
        return row if 0 <= row < len(self._layers) else None

    def _row_rect(self, row: int) -> QRectF:
        return QRectF(
            0,
            self._top_margin() + row * self._row_height(),
            self.width(),
            self._row_height(),
        )

    def _bar_rect(self, row: int, layer: TimelineLayer) -> QRectF:
        row_rect = self._row_rect(row)
        x = self._ms_to_x(layer.start_ms)
        end_x = self._ms_to_x(layer.start_ms + layer.duration_ms)

        return QRectF(
            x,
            row_rect.top() + 5,
            max(4, end_x - x),
            row_rect.height() - 10,
        )

    def _track_rect(self) -> QRectF:
        left = self._label_width()
        right = self.width() - self._right_margin()

        return QRectF(
            left,
            self._top_margin(),
            max(1, right - left),
            max(1, self.height() - self._top_margin() - 8),
        )

    def _ms_to_x(self, ms: int | float) -> float:
        track = self._track_rect()
        ratio = max(0.0, min(1.0, float(ms) / max(1, self._duration_ms)))
        return track.left() + track.width() * ratio

    def _x_to_ms(self, x: float) -> int:
        track = self._track_rect()
        ratio = (x - track.left()) / max(1.0, track.width())
        ratio = max(0.0, min(1.0, ratio))
        return int(round(ratio * self._duration_ms))

    def _snap_ms(self, value: int) -> int:
        return value if self.SNAP_MS <= 1 else int(round(value / self.SNAP_MS) * self.SNAP_MS)

    def _label_width(self) -> int:
        return 130

    def _right_margin(self) -> int:
        return 22

    def _top_margin(self) -> int:
        return 34

    def _row_height(self) -> int:
        return 28

    @staticmethod
    def _text_color_for_background(color: QColor) -> str:
        red = color.red()
        green = color.green()
        blue = color.blue()

        def linearize(channel: int) -> float:
            value = channel / 255.0
            if value <= 0.04045:
                return value / 12.92
            return ((value + 0.055) / 1.055) ** 2.4

        luminance = (
            0.2126 * linearize(red)
            + 0.7152 * linearize(green)
            + 0.0722 * linearize(blue)
        )
        return "#000000" if luminance > 0.179 else "#ffffff"
