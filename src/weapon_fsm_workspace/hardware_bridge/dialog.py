"""Qt editor front-end for all three bridge modes.

Blocking serial commands run in a worker thread, never the UI thread.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from .client import BridgeClient, BridgeMode


class HardwareBridgeDialog(QDialog):
    def __init__(self, parent: QWidget | None = None,
                 current_weapon: Callable[[], tuple[Path, str]] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Live Hardware Bridge")
        self.resize(570, 480)
        self._current_weapon = current_weapon
        self.client = BridgeClient(on_event=lambda text: self._logs.put(f"[device] {text}"))
        self._jobs: queue.Queue[Callable[[], None] | None] = queue.Queue()
        self._logs: queue.Queue[str] = queue.Queue()
        self._worker = threading.Thread(target=self._work, daemon=True, name="bridge-jobs")
        self._worker.start()
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._flush_logs)
        self._timer.start(75)

    def _work(self) -> None:
        while (job := self._jobs.get()) is not None:
            try:
                job()
            except Exception as exc:
                self._logs.put(f"[error] {exc}")

    def _run(self, description: str, job: Callable[[], None]) -> None:
        def task() -> None:
            job()
            self._logs.put(f"[ok] {description}")
        self._jobs.put(task)

    def _flush_logs(self) -> None:
        while True:
            try:
                line = self._logs.get_nowait()
            except queue.Empty:
                return
            self.output.append(line)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.port = QLineEdit("COM5")
        form.addRow("Serial port", self.port)
        self.bank = QLineEdit("Default")
        form.addRow("Weapon bank", self.bank)
        layout.addLayout(form)
        row = QHBoxLayout()
        connect = QPushButton("Connect")
        connect.clicked.connect(lambda: self._run("connected", lambda: self.client.connect(self.port.text())))
        row.addWidget(connect)
        disconnect = QPushButton("Disconnect")
        disconnect.clicked.connect(lambda: self._run("disconnected", self.client.close))
        row.addWidget(disconnect)
        layout.addLayout(row)

        self.mode = QComboBox()
        self.mode.addItems(["1 · Deploy / device inputs", "2 · PC input / MCU FSM", "3 · PC FSM / hardware outputs"])
        layout.addWidget(self.mode)
        apply_mode = QPushButton("Activate selected mode")
        apply_mode.clicked.connect(self._apply_mode)
        layout.addWidget(apply_mode)

        self.deploy = QPushButton("Deploy compiled assets directory to SD (Mode 1)")
        self.deploy.clicked.connect(self._deploy)
        layout.addWidget(self.deploy)
        selected = QPushButton("Compile edited weapon and deploy (existing bank entry)")
        selected.clicked.connect(self._deploy_current_weapon)
        layout.addWidget(selected)

        row = QHBoxLayout()
        trigger = QPushButton("Hold Trigger")
        trigger.pressed.connect(lambda: self._input(0, True))
        trigger.released.connect(lambda: self._input(0, False))
        row.addWidget(trigger)
        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(lambda: self._run("reload tap", self.client.tap_reload))
        row.addWidget(reload_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        for name, button in (("Next weapon", 1), ("Previous weapon", 2)):
            widget = QPushButton(name)
            widget.clicked.connect(lambda checked=False, value=button: self._run(
                f"button {value} tap", lambda: self._tap(value)))
            row.addWidget(widget)
        layout.addLayout(row)

        form = QFormLayout()
        self.asset_path = QLineEdit("assets/lights/diagnostics/rainbow_ring_61.bin")
        form.addRow("SD asset path", self.asset_path)
        layout.addLayout(form)
        row = QHBoxLayout()
        play_light = QPushButton("Play light")
        play_light.clicked.connect(lambda: self._run("light", lambda: self.client.play_light(self.asset_path.text(), True)))
        row.addWidget(play_light)
        stop_light = QPushButton("Stop light")
        stop_light.clicked.connect(lambda: self._run("stop light", self.client.stop_light))
        row.addWidget(stop_light)
        play_audio = QPushButton("Play audio")
        play_audio.clicked.connect(lambda: self._run("audio", lambda: self.client.play_audio(self.asset_path.text())))
        row.addWidget(play_audio)
        layout.addLayout(row)

        layout.addWidget(QLabel("Protocol telemetry / transfer status"))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

    def _apply_mode(self) -> None:
        selected = (BridgeMode.LOCAL, BridgeMode.REMOTE_INPUT, BridgeMode.REMOTE_CONTROL)[self.mode.currentIndex()]
        self._run("mode changed", lambda: self.client.set_mode(selected))

    def _input(self, button: int, pressed: bool) -> None:
        self._run("input", lambda: self.client.input(button, pressed))

    def _tap(self, button: int) -> None:
        import time
        self.client.input(button, True)
        time.sleep(0.065)
        self.client.input(button, False)

    def _deploy_current_weapon(self) -> None:
        if self._current_weapon is None:
            self._logs.put("[error] no editor document available")
            return
        source, yaml_text = self._current_weapon()
        # The original name/bank entry must already be on the SD. Only replace
        # its binary and assets: never overwrite the existing six-bank manifest.
        bank = self.bank.text().strip()
        if not bank:
            self._logs.put("[error] bank name is required")
            return
        self._run("compiled edited weapon deployed", lambda: self._compile_and_deploy(
            source, yaml_text, bank))

    def _compile_and_deploy(self, source: Path, content: str, bank: str) -> None:
        import tempfile
        from weapon_fsm_workspace.sd_export import SdCardExporter
        with tempfile.TemporaryDirectory(prefix="blaster-live-export-") as tmpdir:
            # Keep source in its original folder to resolve relative audio and
            # lighting paths; remove it immediately after compilation.
            import uuid
            temporary_source = source.with_name(f".bridge-{uuid.uuid4().hex}.yaml")
            try:
                temporary_source.write_text(content, encoding="utf-8")
                root = Path(tmpdir)
                SdCardExporter(root).export_weapon(
                    temporary_source, bank_name=bank, weapon_name=source.stem)
            finally:
                temporary_source.unlink(missing_ok=True)
            for asset in sorted((root / "assets").rglob("*")):
                if asset.is_file() and asset.name != "weapons_manifest.bin":
                    self.client.deploy_file(asset, asset.relative_to(root).as_posix())
            self.client.activate()

    def _deploy(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Choose compiled SD assets directory")
        if chosen:
            root = Path(chosen)
            # Select SD root containing assets/ or the assets/ folder itself.
            if (root / "assets").is_dir():
                self._run("SD assets uploaded", lambda: self.client.deploy_tree(root, ""))
            elif root.name == "assets":
                self._run("SD assets uploaded", lambda: self.client.deploy_tree(root, "assets"))
            else:
                self._logs.put("[error] select an SD export folder containing assets/")

    def send_editor_input(self, button: int, pressed: bool) -> None:
        if self.client.mode == BridgeMode.REMOTE_INPUT:
            self._input(button, pressed)

    def send_rendered_frame(self, rgb: bytes) -> None:
        if self.client.mode == BridgeMode.REMOTE_CONTROL:
            self._run("LED frame", lambda: self.client.led_frame(rgb))

    def send_editor_command(self, command: object) -> bool:
        if self.client.mode != BridgeMode.REMOTE_CONTROL:
            return False
        kind = getattr(command, "type", "")
        payload = getattr(command, "payload", {})
        path = str(payload.get("path", ""))
        if kind == "play_audio" and path:
            import re
            clip_id = str(payload.get("clip", ""))
            if self._current_weapon and clip_id:
                source, _ = self._current_weapon()
                slug = lambda value: re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
                path = f"assets/weapons/{slug(self.bank.text().strip())}/{slug(source.stem)}/audio/{slug(clip_id)}.wav"
            self._run(kind, lambda: self.client.play_audio(path, payload.get("mode") == "loop"))
        elif kind == "stop_audio":
            self._run(kind, self.client.stop_audio)
        elif kind == "play_light" and path:
            # Lighting is preview-rendered by the PC and streamed as LED_FRAME.
            # Do not start an unrelated compiled MCU sequence here.
            return False
        elif kind == "stop_light":
            self._run(kind, self.client.stop_light)
        else:
            return False
        return True

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._jobs.put(self.client.close)
        super().closeEvent(event)
