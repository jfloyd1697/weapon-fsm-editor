from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GunControlPanel(QWidget):
    equip_requested = pyqtSignal()
    trigger_pressed_requested = pyqtSignal()
    trigger_held_requested = pyqtSignal()
    trigger_released_requested = pyqtSignal()
    reload_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)

        group = QGroupBox("Gun Controls")
        group_layout = QVBoxLayout(group)

        self._status_label = QLabel("Trigger: released")

        row = QHBoxLayout()

        self._equip_button = QPushButton("Equip")
        self._reload_button = QPushButton("Reload")
        self._trigger_button = QPushButton("Trigger")

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.setInterval(100)

        row.addWidget(self._equip_button)
        row.addWidget(self._reload_button)
        row.addWidget(self._trigger_button)

        group_layout.addLayout(row)
        group_layout.addWidget(self._status_label)

        root.addWidget(group)
        root.addStretch()

        self._equip_button.clicked.connect(self.equip_requested.emit)
        self._reload_button.clicked.connect(self.reload_requested.emit)
        self._trigger_button.pressed.connect(self._on_trigger_pressed)
        self._trigger_button.released.connect(self._on_trigger_released)
        self._hold_timer.timeout.connect(self._on_trigger_held)

    def _on_trigger_pressed(self) -> None:
        self._status_label.setText("Trigger: pressed")
        self.trigger_pressed_requested.emit()
        self._hold_timer.start()

    def _on_trigger_held(self) -> None:
        if self._trigger_button.isDown():
            self._status_label.setText("Trigger: held")
            self.trigger_held_requested.emit()

    def _on_trigger_released(self) -> None:
        self._hold_timer.stop()
        self._status_label.setText("Trigger: released")
        self.trigger_released_requested.emit()

    def reset_trigger(self) -> None:
        self._hold_timer.stop()
        self._status_label.setText("Trigger: released")
