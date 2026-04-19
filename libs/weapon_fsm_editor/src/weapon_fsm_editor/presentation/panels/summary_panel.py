from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from weapon_fsm_core.application.simulate_event import SimulationService


class SummaryPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.state = QLabel("-")
        self.last_transition = QLabel("-")
        self.pending_events = QLabel("-")

        self._variable_labels: dict[str, QLabel] = {}
        self._variables_group = QGroupBox("Runtime Variables")
        self._variables_layout = QFormLayout(self._variables_group)

        self._summary_group = QGroupBox("Simulation Summary")
        self._summary_layout = QFormLayout(self._summary_group)
        self._summary_layout.addRow("State:", self.state)
        self._summary_layout.addRow("Last Transition:", self.last_transition)
        self._summary_layout.addRow("Pending Events:", self.pending_events)

        root = QVBoxLayout(self)
        root.addWidget(self._summary_group)
        root.addWidget(self._variables_group)
        root.addStretch()

    def initialize_for_weapon(self, simulation: SimulationService) -> None:
        self._clear_variable_rows()

        runtime = simulation.runtime
        for name in sorted(runtime.variables.keys()):
            value_label = QLabel("-")
            self._variable_labels[name] = value_label
            self._variables_layout.addRow(f"{name}:", value_label)

        self.update_summary(simulation)

    def update_summary(self, simulation: SimulationService) -> None:
        runtime = simulation.runtime
        self.state.setText(str(runtime.current_state))
        self.last_transition.setText(runtime.last_transition_id or "-")

        if runtime.pending_events:
            pending_text = ", ".join(
                f"{event.event_id}({event.delay_ms} ms)"
                for event in runtime.pending_events
            )
        else:
            pending_text = "-"
        self.pending_events.setText(pending_text)

        for name, label in self._variable_labels.items():
            value = runtime.variables.get(name, "-")
            label.setText(str(value))

    def _clear_variable_rows(self) -> None:
        self._variable_labels.clear()

        while self._variables_layout.rowCount() > 0:
            self._variables_layout.removeRow(0)