import traceback
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
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

from weapon_fsm_audio import AudioLibraryBrowser
from weapon_fsm_audio.infrastructure.runtime import PortAudioBackend

from weapon_fsm_core import ProfileRepository, SimulationService
from weapon_fsm_core.domain.model import GunConfig, WeaponConfig
from weapon_fsm_core.domain.validation import ProfileValidator
from weapon_fsm_core.infrastructure.yaml.profile_builder import ProfileYamlBuilder
from weapon_fsm_hardware import RuntimeCommandDispatcher

from weapon_fsm_workspace.hardware_bridge.dialog import HardwareBridgeDialog

from weapon_fsm_lights.infrastructure.runtime import QtLightBackend
from weapon_fsm_lights.presentation.led_canvas_widget import LedPreviewPanel

from ..infrastructure.runtime import RuntimeCommandBridge
from .graph.machine_view import MachineWidget
from .panels.event_panel import EventPanel
from .panels.gun_control_panel import GunControlPanel
from .panels.summary_panel import SummaryPanel
from .weapon_document_editor.editor import WeaponDocumentEditor


MAX_RUNTIME_LOG_BLOCKS = 4000


def _format_runtime_variables(variables: dict[str, object]) -> str:
    parts = [f"{key}={value}" for key, value in sorted(variables.items())]
    return ", ".join(parts)


def get_call_trace() -> str:
    return "".join(traceback.format_stack())


class MainWindow(QMainWindow):
    def __init__(self, gun_path: Path, weapon_path: Path) -> None:
        super().__init__()
        self.setWindowTitle("Weapon FSM Dashboard")
        self._gun_path = gun_path
        self._weapon_path = weapon_path
        self._repository = ProfileRepository()
        self._validator = ProfileValidator()
        self._profile_builder = ProfileYamlBuilder()

        self._simulation: SimulationService | None = None
        self._gun: GunConfig | None = None
        self._weapon: WeaponConfig | None = None
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.document().setMaximumBlockCount(MAX_RUNTIME_LOG_BLOCKS)

        self._audio_backend = PortAudioBackend(log=self._append_runtime_log)
        self.led_preview_panel = LedPreviewPanel(self)
        self.led_preview_panel.player.frame_changed.connect(self._send_rendered_frame)
        self._light_backend = QtLightBackend(log=self._append_runtime_log, preview_panel=self.led_preview_panel)
        self._command_bridge = RuntimeCommandBridge(
            RuntimeCommandDispatcher(audio=self._audio_backend, lights=self._light_backend)
        )

        self._hardware_bridge_dialog: HardwareBridgeDialog | None = None
        self.audio_library = AudioLibraryBrowser(self._audio_backend, parent=self)
        self.gun_editor = QTextEdit()
        self.weapon_editor = WeaponDocumentEditor(self)
        self.behavior_widget = MachineWidget("Weapon Behavior")
        self.event_panel = EventPanel()
        self.summary_panel = SummaryPanel()
        self.gun_control_panel = GunControlPanel(self)

        self._clock_timer = QTimer(self)
        self._clock_timer.setSingleShot(True)
        self._clock_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._clock_timer.timeout.connect(self._advance_time)
        self._clock_last_ns = time.monotonic_ns()
        self._last_view_state: tuple[str, str | None, frozenset[str]] | None = None

        from weapon_fsm_workspace.paths import ASSETS_ROOT
        example_layout = ASSETS_ROOT / "lights/layouts/cpx_ring_61_outside_in.json"
        self.led_preview_panel.set_example_layout_path(example_layout)

        self._build_ui()
        self._load_documents_from_disk(gun_path, weapon_path)

    def _open_hardware_bridge(self) -> None:
        if self._hardware_bridge_dialog is None:
            self._hardware_bridge_dialog = HardwareBridgeDialog(
                self,
                current_weapon=lambda: (self._weapon_path, self.weapon_editor.toPlainText()),
            )
        self._hardware_bridge_dialog.show()
        self._hardware_bridge_dialog.raise_()

    def _send_rendered_frame(self, index: int, frame) -> None:
        dialog = self._hardware_bridge_dialog
        if dialog is None or dialog.client.mode != 2:
            return
        asset = self.led_preview_panel.canvas.asset
        if asset is None:
            return
        count = max((led.index if led.index is not None else order)
                    for order, led in enumerate(asset.leds)) + 1
        if count > 128:
            return
        rgb = bytearray(count * 3)
        for order, led in enumerate(asset.leds):
            state = frame.leds.get(led.id)
            if state is None:
                continue
            color = QColor(state[0])
            brightness = min(1.0, max(0.0, float(state[1])))
            pos = (led.index if led.index is not None else order) * 3
            rgb[pos:pos+3] = bytes(round(channel * brightness)
                                  for channel in (color.red(), color.green(), color.blue()))
        dialog.send_rendered_frame(bytes(rgb))

    def _append_runtime_log(self, message: str) -> None:
        self.log_output.append(message)

    def _build_ui(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        bridge_btn = QPushButton("Live Hardware")
        bridge_btn.clicked.connect(self._open_hardware_bridge)
        toolbar.addWidget(bridge_btn)

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

        save_gun_btn = QPushButton("Save Gun")
        save_gun_btn.clicked.connect(self._save_gun)
        toolbar.addWidget(save_gun_btn)

        save_gun_as_btn = QPushButton("Save Gun As")
        save_gun_as_btn.clicked.connect(self._save_gun_as)
        toolbar.addWidget(save_gun_as_btn)

        save_weapon_btn = QPushButton("Save Weapon")
        save_weapon_btn.clicked.connect(self._save_weapon)
        toolbar.addWidget(save_weapon_btn)

        save_weapon_as_btn = QPushButton("Save Weapon As")
        save_weapon_as_btn.clicked.connect(self._save_weapon_as)
        toolbar.addWidget(save_weapon_as_btn)

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

        left.addWidget(self.audio_library)
        left.addWidget(gun_editor_container)
        left.addWidget(weapon_editor_container)

        center.addWidget(self.behavior_widget)

        right.addWidget(self.gun_control_panel)
        right.addWidget(self.event_panel)
        right.addWidget(self.summary_panel)
        right.addWidget(self.led_preview_panel)
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

    def _save_gun(self) -> None:
        self._save_gun_to_path(self._gun_path)

    def _save_gun_as(self) -> None:
        current_path = self._gun_path or self._gun_path
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save gun",
            str(current_path) if current_path is not None else str(Path.cwd() / "gun.yaml"),
            "YAML files (*.yaml *.yml)",
        )
        if file_name:
            self._save_gun_to_path(Path(file_name))

    def _save_weapon(self) -> None:
        self._save_weapon_to_path(self._weapon_path)

    def _save_weapon_as(self) -> None:
        current_path = self._weapon_path or self._weapon_path
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save weapon",
            str(current_path) if current_path is not None else str(Path.cwd() / "weapon.yaml"),
            "YAML files (*.yaml *.yml)",
        )
        if file_name:
            self._save_weapon_to_path(Path(file_name))

    def _save_gun_to_path(self, path: Path | None) -> None:
        try:
            gun = self._repository.load_gun_text(self.gun_editor.toPlainText())
            normalized = self._profile_builder.dump_gun(gun)
            target = path or self._gun_path
            if target is None:
                raise RuntimeError("No gun path is set")
            target.write_text(normalized, encoding="utf-8")
            self._gun_path = target
            self.gun_editor.setPlainText(normalized)
            self.statusBar().showMessage(f"Saved gun: {target.name}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save gun failed", repr(exc))

    def _save_weapon_to_path(self, path: Path | None) -> None:
        try:
            # weapon = self._repository.load_weapon_text(
            #     self.weapon_editor.toPlainText(),
            #     source_path=path or self._weapon_path,
            # )
            # normalized = self._profile_builder.dump_weapon(weapon)
            target = path or self._weapon_path
            if target is None:
                raise RuntimeError("No weapon path is set")
            normalized = self.weapon_editor.toPlainText()
            target.write_text(normalized, encoding="utf-8")
            self._weapon_path = target
            self.weapon_editor.setPlainText(normalized)
            self._apply_documents(self.gun_editor.toPlainText(), normalized)
            self.statusBar().showMessage(f"Saved weapon: {target.name}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save weapon failed", repr(exc))

    def _apply_documents(self, gun_text: str, weapon_text: str) -> None:
        try:
            gun = self._repository.load_gun_text(gun_text)
            weapon = self._repository.load_weapon_text(
                weapon_text,
                source_path=self._repository.asset_root_for_profile(self._weapon_path),
            )
            issues = self._validator.validate(gun, weapon)

            asset_errors = [
                issue for issue in issues
                if issue.path.startswith(("clips.", "light_sequences."))
            ]
            if asset_errors:
                summary = "\n\n".join(f"{issue.path}: {issue.message}" for issue in asset_errors)
                raise FileNotFoundError(summary)

            self._gun = gun
            self._weapon = weapon
            self._simulation = SimulationService(gun, weapon)
            self._clock_last_ns = time.monotonic_ns()
            self._last_view_state = None
            self._schedule_next_tick()
            self.weapon_editor.set_source_path(self._repository.asset_root_for_profile(self._weapon_path))
            self.weapon_editor.set_gun_config(self._gun)
            self.audio_library.set_weapon(self._weapon)

            self.event_panel.set_events(list(gun.events))
            self.gun_control_panel.reset_trigger()
            self.summary_panel.initialize_for_weapon(self._simulation)

            self._command_bridge.reset()
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

        self._command_bridge.reset()
        self._simulation.reset()
        self._clock_last_ns = time.monotonic_ns()
        self._schedule_next_tick()
        self.gun_control_panel.reset_trigger()
        self.log_output.append("[system] weapon equipped")
        self._dispatch_event("on_equip")

    def _dispatch_trigger_pressed(self) -> None:
        if self._hardware_bridge_dialog and self._hardware_bridge_dialog.client.mode == 1:
            self._hardware_bridge_dialog.send_editor_input(0, True)
            return
        self._dispatch_named_event("trigger_pressed")

    def _dispatch_trigger_held(self) -> None:
        if self._hardware_bridge_dialog and self._hardware_bridge_dialog.client.mode == 1:
            return
        self._dispatch_named_event("trigger_held")

    def _dispatch_trigger_released(self) -> None:
        if self._hardware_bridge_dialog and self._hardware_bridge_dialog.client.mode == 1:
            self._hardware_bridge_dialog.send_editor_input(0, False)
            return
        self._dispatch_named_event("trigger_released")

    def _dispatch_reload(self) -> None:
        if self._hardware_bridge_dialog and self._hardware_bridge_dialog.client.mode == 1:
            self._hardware_bridge_dialog._run("reload tap", self._hardware_bridge_dialog.client.tap_reload)
            return
        self._dispatch_named_event("reload_pressed")

    def _dispatch_named_event(self, event_id: str) -> None:
        if self._gun is None or event_id not in self._gun.events:
            self.log_output.append(f"[warning] event not defined in gun config: {event_id}")
            return
        self._dispatch_event(event_id)

    def _dispatch_event(self, event_id: str) -> None:
        dialog = self._hardware_bridge_dialog
        if dialog is not None and dialog.client.mode == 1:
            input_events = {
                "trigger_pressed": (0, True),
                "trigger_released": (0, False),
            }
            if event_id in input_events:
                button, pressed = input_events[event_id]
                dialog.send_editor_input(button, pressed)
            elif event_id == "reload_pressed":
                dialog._run("reload tap", dialog.client.tap_reload)
            else:
                self._append_runtime_log(f"[remote input] unsupported event: {event_id}")
            return
        if self._simulation is None:
            return

        self._advance_time()
        records = self._simulation.dispatch_external_event(event_id)
        self._handle_records(records, source_prefix=None)
        self._schedule_next_tick()

    def _handle_records(self, records, source_prefix: str | None) -> None:
        if not records:
            return

        lines: list[str] = []
        for record in records:
            result = record.result
            if not result.accepted and result.event_id == "trigger_held" and (
                result.reason or ""
            ).startswith("No transition for event"):
                continue

            if result.accepted:
                transition_id = result.transition.id if result.transition else "?"
                prefix = f"[{source_prefix}] " if source_prefix is not None else f"[{record.machine_id}] "
                if source_prefix is not None:
                    lines.append(
                        f"{prefix}{result.event_id}: {result.previous_state} -> {result.current_state} via {transition_id}"
                    )
                else:
                    lines.append(
                        f"{prefix}event={result.event_id} "
                        f"{result.previous_state} -> {result.current_state} via {transition_id}"
                    )

                lines.append(
                    f"[vars] before: {_format_runtime_variables(result.variables_before)}"
                )
                lines.append(
                    f"[vars] after:  {_format_runtime_variables(result.variables_after)}"
                )

                for emitted_event in result.emitted_events:
                    lines.append(f"[emit] {emitted_event}")

                for scheduled in result.scheduled_events:
                    lines.append(
                        f"[scheduler] scheduled {scheduled.event_id} in {scheduled.delay_ms} ms"
                    )

                if self._hardware_bridge_dialog and self._hardware_bridge_dialog.client.mode == 2:
                    for command in result.commands:
                        if command.type == "play_light":
                            payload = command.payload
                            self._light_backend.play_light(
                                sequence=str(payload.get("sequence", "")),
                                path=str(payload.get("path", "")),
                                mode=str(payload.get("mode", "once")),
                            )
                        elif command.type == "stop_light":
                            self._light_backend.stop_light()
                            self._hardware_bridge_dialog.send_editor_command(command)
                        else:
                            self._hardware_bridge_dialog.send_editor_command(command)
                else:
                    self._command_bridge.dispatch_commands(result.commands)
                for command in result.commands:
                    lines.append(f"[command] {command.type}: {command.payload}")
            else:
                prefix = f"[{source_prefix}] " if source_prefix is not None else f"[{record.machine_id}] "
                if source_prefix is not None:
                    lines.append(
                        f"{prefix}{result.event_id} ignored in {result.current_state}: {result.reason}"
                    )
                else:
                    lines.append(
                        f"{prefix}event={result.event_id} ignored in "
                        f"{result.current_state}: {result.reason}"
                    )

            lines.append("")

        if not lines:
            return
        self.log_output.append("\n".join(lines))
        self._refresh_views()

    def _schedule_next_tick(self) -> None:
        if self._simulation is None:
            self._clock_timer.stop()
            return
        delay_ms = self._simulation.runtime.time_until_next_event_ms()
        if delay_ms is None:
            self._clock_timer.stop()
        else:
            self._clock_timer.start(max(1, delay_ms))

    def _advance_time(self) -> None:
        now_ns = time.monotonic_ns()
        elapsed_ms = (now_ns - self._clock_last_ns) // 1_000_000
        self._clock_last_ns += elapsed_ms * 1_000_000
        if self._hardware_bridge_dialog is not None and self._hardware_bridge_dialog.client.mode == 1:
            self._clock_last_ns = now_ns
            self._clock_timer.stop()
            return
        if self._simulation is None:
            return
        if self._simulation.runtime.time_until_next_event_ms() is not None:
            records = self._simulation.advance_time(int(elapsed_ms))
            self._handle_records(records, source_prefix="timer")
        self._schedule_next_tick()

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

        view_state = (current_state, last_id, frozenset(valid_ids))
        if view_state != self._last_view_state:
            self.behavior_widget.set_active_state(current_state, valid_ids, last_id)
            self._last_view_state = view_state
        self.summary_panel.update_summary(self._simulation)

    def _reset_simulation(self) -> None:
        if self._simulation is None:
            return
        self._command_bridge.reset()
        self._simulation.reset()
        self._clock_last_ns = time.monotonic_ns()
        self._schedule_next_tick()
        self.gun_control_panel.reset_trigger()
        self.log_output.append("[system] simulation reset")
        self._refresh_views()
