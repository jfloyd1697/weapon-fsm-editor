from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget


class EventPanel(QWidget):
    event_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.addWidget(QLabel("Gun Events"))
        self._layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._container)

        root = QVBoxLayout(self)
        root.addWidget(scroll)

    def set_events(self, event_ids: list[str]) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self._layout.addStretch(1)

        for event_id in event_ids[::-1]:
            button = QPushButton(event_id)
            button.clicked.connect(lambda _checked=False, e=event_id: self.event_requested.emit(e))
            self._layout.insertWidget(1, button)
