import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from weapon_fsm_core.domain.model import WeaponConfig

from .machine_html_builder import MachineHtmlBuilder


class _DebugPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        print(f"[web:{level.name}] {source_id}:{line_number} {message}")
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class _MachineWebView(QWebEngineView):
    def __init__(self, parent_widget: "MachineWidget", parent=None) -> None:
        super().__init__(parent)
        self._parent_widget = parent_widget
        self.setPage(_DebugPage(self))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta_y = event.angleDelta().y()
            if delta_y > 0:
                self._parent_widget.zoom_graph(1.15)
            elif delta_y < 0:
                self._parent_widget.zoom_graph(1.0 / 1.15)
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._parent_widget.fit_graph()
            event.accept()
            return
        super().keyPressEvent(event)


class MachineWidget(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self._title = title
        self._view = _MachineWebView(self, self)
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._fit_button = QPushButton("Fit")
        self._fit_button.clicked.connect(self.fit_graph)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(4, 4, 4, 0)
        controls_layout.setSpacing(4)
        controls_layout.addWidget(self._fit_button)
        controls_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(controls_layout)
        layout.addWidget(self._view)

        self._machine: Optional[WeaponConfig] = None
        self._machine_signature: Optional[str] = None
        self._active_state_id: Optional[str] = None
        self._valid_transition_ids: set[str] = set()
        self._last_transition_id: Optional[str] = None
        self._page_ready = False

        self._html_dir = Path(tempfile.gettempdir()) / f"weapon_fsm_{self._safe_name(title)}"
        self._html_dir.mkdir(parents=True, exist_ok=True)

        self._html_path = self._html_dir / "graph.html"
        self._runtime_js_path = self._html_dir / "runtime.js"

        self._builder = MachineHtmlBuilder(title, runtime_js_name="runtime.js")
        self._ensure_runtime_js()

        self._view.loadFinished.connect(self._on_load_finished)

        self._fit_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self._fit_shortcut.activated.connect(self.fit_graph)

    def set_machine(self, machine: WeaponConfig, positions=None) -> None:
        del positions
        self._machine = machine
        new_signature = self._machine_signature_for(machine)

        if new_signature != self._machine_signature:
            self._machine_signature = new_signature
            self._reload_machine_html()
        else:
            self._apply_highlighting()

    def set_active_state(
        self,
        active_state_id: str,
        valid_transition_ids: set[str],
        last_transition_id: Optional[str],
    ) -> None:
        self._active_state_id = active_state_id
        self._valid_transition_ids = set(valid_transition_ids)
        self._last_transition_id = last_transition_id
        self._apply_highlighting()

    def refresh_palette(self) -> None:
        if self._machine is None:
            return
        self._reload_machine_html()

    def fit_graph(self) -> None:
        if not self._page_ready:
            return
        self._view.page().runJavaScript("window.fitMachineGraph && window.fitMachineGraph();")

    def zoom_graph(self, scale_factor: float) -> None:
        if not self._page_ready:
            return
        self._view.page().runJavaScript(f"window.zoomMachineGraph && window.zoomMachineGraph({scale_factor});")

    def _reload_machine_html(self) -> None:
        if self._machine is None:
            return

        self._page_ready = False
        self._ensure_runtime_js()

        html = self._builder.build_html(
            machine=self._machine,
            active_state_id=self._active_state_id,
            valid_transition_ids=self._valid_transition_ids,
            last_transition_id=self._last_transition_id,
        )

        self._html_path.write_text(html, encoding="utf-8")
        self._view.load(QUrl.fromLocalFile(str(self._html_path)))

    def _on_load_finished(self, ok: bool) -> None:
        print(f"[graph] load finished: ok={ok} path={self._html_path}")
        self._page_ready = ok
        if not ok:
            return
        self._apply_highlighting()
        self.fit_graph()

    def _apply_highlighting(self) -> None:
        if not self._page_ready:
            return

        active_state_json = json.dumps(self._active_state_id)
        valid_transition_ids_json = json.dumps(sorted(self._valid_transition_ids))
        last_transition_json = json.dumps(self._last_transition_id)

        js = f"""
window.updateMachineHighlighting &&
window.updateMachineHighlighting(
    {active_state_json},
    {valid_transition_ids_json},
    {last_transition_json}
);
"""
        self._view.page().runJavaScript(js)

    def _ensure_runtime_js(self) -> None:
        source_path = Path(__file__).with_name("runtime.js")
        shutil.copyfile(source_path, self._runtime_js_path)

    def _machine_signature_for(self, machine: WeaponConfig) -> str:
        payload = {
            "states": [{"id": state.id, "label": state.label} for state in machine.states.values()],
            "transitions": [
                {
                    "id": transition.id,
                    "source": transition.source,
                    "target": transition.target,
                    "trigger": transition.trigger,
                }
                for transition in machine.transitions
            ],
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _safe_name(self, title: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "_" for ch in title)
