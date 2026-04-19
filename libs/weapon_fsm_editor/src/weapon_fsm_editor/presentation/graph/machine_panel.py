from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MachinePanel(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, title: str, content: QWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._title_label = QLabel(title)
        self._close_button = QPushButton("×")
        self._close_button.setFixedWidth(28)
        self._close_button.clicked.connect(self.close_requested.emit)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(6, 6, 6, 0)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._close_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header_layout)
        layout.addWidget(content)