import traceback
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_core import ProfileRepository, SimulationService
from weapon_fsm_core.domain.model import GunConfig, WeaponConfig
from weapon_fsm_core.domain.validation import ProfileValidator

from .graph.machine_view import MachineWidget
from .panels.event_panel import EventPanel
from .panels.gun_control_panel import GunControlPanel
from .panels.summary_panel import SummaryPanel


def _format_runtime_variables(variables: dict[str, object]) -> str:
    parts = [f"{key}={value}" for key, value in sorted(variables.items())]
    return ", ".join(parts)


class MainWindow(QMainWindow):
    def __init__(self, gun_path: Path, weapon_path: Path) -> None:
        super().__init__()
        self.setWindowTitle("Weapon FSM Dashboard")
        self._gun_path = gun_path
        self._weapon_path = weapon_path
        self._repository = ProfileRepository()
        self._validator = ProfileValidator()
        self._simulation: SimulationService | None = None
        self._gun: GunConfig | None = None
        self._weapon: WeaponConfig | None = None

        self.gun_editor = QTextEdit()
        self.weapon_editor = QTextEdit()
        self.behavior_widget = MachineWidget("Weapon Behavior")
        self.event_panel = EventPanel()
        self.summary_panel = SummaryPanel()
        self.gun_control_panel = GunControlPanel(self)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(50)
        self._clock_timer.timeout.connect(self._advance_time)
        self._clock_timer.start()

        self._build_ui()
        self._load_documents_from_disk(gun_path, weapon_path)

    def _build_ui(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        open_gun_btn = QPushButton("Open Gun")
        open_gun_btn.clicked.connect(self._open_gun)
        toolbar.addWidget(open_gun_btn)

        open_weapon_btn = QPushButton("Open Weapon")
        open_weapon_btn.clicked.connect(self._open_weapon)
        toolbar.addWidget(open_weapon_btn)

        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(lambda: self._load_documents_from_disk(self._gun_path, self._weapon_path))
        toolbar.addWidget(reload_btn)

        apply_btn = QPushButton("Apply Text")
        apply_btn.clicked.connect(self._apply_editor_text)
        toolbar.addWidget(apply_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_simulation)
        toolbar.addWidget(reset_btn)

        root = QSplitter(Qt.Orientation.Horizontal)
        left = QSplitter(Qt.Orientation.Vertical)
        center = QSplitter(Qt.Orientation.Vertical)
        right = QSplitter(Qt.Orientation.Vertical)

        gun_editor_container = QWidget()
        gun_editor_layout = QVBoxLayout(gun_editor_container)
        gun_editor_layout.addWidget(QLabel("Gun YAML"))
        gun_editor_layout.addWidget(self.gun_editor)

        weapon_editor_container = QWidget()
        weapon_editor_layout = QVBoxLayout(weapon_editor_container)
        weapon_editor_layout.addWidget(QLabel("Weapon YAML"))
        weapon_editor_layout.addWidget(self.weapon_editor)

        left.addWidget(gun_editor_container)
        left.addWidget(weapon_editor_container)

        center.addWidget(self.behavior_widget)

        right.addWidget(self.gun_control_panel)
        right.addWidget(self.event_panel)
        right.addWidget(self.summary_panel)
        right.addWidget(self.log_output)

        root.addWidget(left)
        root.addWidget(center)
        root.addWidget(right)
        root.setSizes([520, 760, 340])

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())

        self.event_panel.event_requested.connect(self._dispatch_event)
        self.gun_control_panel.equip_requested.connect(self._on_equip)
        self.gun_control_panel.trigger_pressed_requested.connect(self._dispatch_trigger_pressed)
        self.gun_control_panel.trigger_held_requested.connect(self._dispatch_trigger_held)
        self.gun_control_panel.trigger_released_requested.connect(self._dispatch_trigger_released)
        self.gun_control_panel.reload_requested.connect(self._dispatch_reload)

    def _open_gun(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open gun",
            str(self._gun_path.parent),
            "YAML files (*.yaml *.yml)",
        )
        if file_name:
            self._load_documents_from_disk(Path(file_name), self._weapon_path)

    def _open_weapon(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open weapon",
            str(self._weapon_path.parent),
            "YAML files (*.yaml *.yml)",
        )
        if file_name:
            self._load_documents_from_disk(self._gun_path, Path(file_name))

    def _load_documents_from_disk(self, gun_path: Path, weapon_path: Path) -> None:
        try:
            gun_text = gun_path.read_text(encoding="utf-8")
            weapon_text = weapon_path.read_text(encoding="utf-8")
            self.gun_editor.setPlainText(gun_text)
            self.weapon_editor.setPlainText(weapon_text)
            self._gun_path = gun_path
            self._weapon_path = weapon_path
            self._apply_documents(gun_text, weapon_text)
            self.statusBar().showMessage(f"Loaded {gun_path.name} + {weapon_path.name}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Load failed", str(exc))

    def _apply_editor_text(self) -> None:
        self._apply_documents(self.gun_editor.toPlainText(), self.weapon_editor.toPlainText())

    def _apply_documents(self, gun_text: str, weapon_text: str) -> None:
        try:
            gun = self._repository.load_gun_text(gun_text)
            weapon = self._repository.load_weapon_text(weapon_text)
            issues = self._validator.validate(gun, weapon)

            self._gun = gun
            self._weapon = weapon
            self._simulation = SimulationService(gun, weapon)

            self.event_panel.set_events(list(gun.events))
            self.gun_control_panel.reset_trigger()
            self.summary_panel.initialize_for_weapon(self._simulation)

            self.log_output.clear()
            for issue in issues:
                self.log_output.append(f"[validation] {issue.path}: {issue.message}")

            self.behavior_widget.set_machine(weapon)
            self._refresh_views()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            QMessageBox.critical(self, "Apply failed", repr(exc))


    def _on_equip(self) -> None:
        if self._simulation is None:
            return

        self._simulation.reset()
        self.gun_control_panel.reset_trigger()
        self.log_output.append("[system] weapon equipped")
        self._dispatch_event("on_equip")

    def _dispatch_trigger_pressed(self) -> None:
        self._dispatch_named_event("trigger_pressed")

    def _dispatch_trigger_held(self) -> None:
        self._dispatch_named_event("trigger_held")

    def _dispatch_trigger_released(self) -> None:
        self._dispatch_named_event("trigger_released")

    def _dispatch_reload(self) -> None:
        self._dispatch_named_event("reload_pressed")

    def _dispatch_named_event(self, event_id: str) -> None:
        if self._gun is None or event_id not in self._gun.events:
            self.log_output.append(f"[warning] event not defined in gun config: {event_id}")
            return
        self._dispatch_event(event_id)

    def _dispatch_event(self, event_id: str) -> None:
        if self._simulation is None:
            return

        records = self._simulation.dispatch_external_event(event_id)
        for record in records:
            result = record.result

            if result.accepted:
                transition_id = result.transition.id if result.transition else "?"
                self.log_output.append(
                    f"[{record.machine_id}] event={result.event_id} "
                    f"{result.previous_state} -> {result.current_state} via {transition_id}"
                )

                self.log_output.append(
                    f"[vars] before: {_format_runtime_variables(result.variables_before)}"
                )
                self.log_output.append(
                    f"[vars] after:  {_format_runtime_variables(result.variables_after)}"
                )

                for emitted_event in result.emitted_events:
                    self.log_output.append(f"[emit] {emitted_event}")

                for scheduled in result.scheduled_events:
                    self.log_output.append(
                        f"[scheduler] scheduled {scheduled.event_id} in {scheduled.delay_ms} ms"
                    )

                for command in result.commands:
                    self.log_output.append(f"[command] {command.type}: {command.payload}")
            else:
                self.log_output.append(
                    f"[{record.machine_id}] event={result.event_id} ignored in "
                    f"{result.current_state}: {result.reason}"
                )

            self.log_output.append("")

        self._refresh_views()

    def _advance_time(self) -> None:
        if self._simulation is None:
            return

        records = self._simulation.advance_time(50)
        if not records:
            return

        for record in records:
            result = record.result
            if result.accepted:
                transition_id = result.transition.id if result.transition else "?"
                self.log_output.append(
                    f"[timer] {result.event_id}: {result.previous_state} -> {result.current_state} via {transition_id}"
                )
        self._refresh_views()

    def _refresh_views(self) -> None:
        if self._simulation is None or self._weapon is None:
            return

        try:
            valid_ids = {t.id for t in self._simulation.runtime.valid_transitions()}
        except Exception:
            traceback.print_exc()
            valid_ids = set()
        last_id = self._simulation.runtime.last_transition_id
        current_state = self._simulation.runtime.current_state

        self.behavior_widget.set_active_state(current_state, valid_ids, last_id)
        self.summary_panel.update_summary(self._simulation)

    def _reset_simulation(self) -> None:
        if self._simulation is None:
            return
        self._simulation.reset()
        self.gun_control_panel.reset_trigger()
        self.log_output.append("[system] simulation reset")
        self._refresh_views()
