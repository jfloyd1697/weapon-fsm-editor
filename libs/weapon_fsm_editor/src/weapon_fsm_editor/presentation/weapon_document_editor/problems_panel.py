from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .diagnostics import EditorDiagnostic


class ProblemsPanel(QWidget):
    navigate_requested = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._list = QListWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)
        self._list.itemActivated.connect(self._on_item_activated)

    def set_diagnostics(self, diagnostics: list[EditorDiagnostic]) -> None:
        self._list.clear()
        for diagnostic in diagnostics:
            text = f"{diagnostic.severity.value.upper()}: line {diagnostic.line_start + 1}: {diagnostic.message}"
            item = QListWidgetItem(text)
            item.setData(256, diagnostic.line_start)
            self._list.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        line = int(item.data(256))
        self.navigate_requested.emit(line)
