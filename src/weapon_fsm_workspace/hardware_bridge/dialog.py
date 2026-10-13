"""Qt editor front-end for all three bridge modes.

Blocking serial commands run in a worker thread, never the UI thread.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable

from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .client import BridgeClient, BridgeMode, FileType, RemoteFile


class HardwareBridgeDialog(QDialog):
    def __init__(self, parent: QWidget | None = None,
                 current_weapon: Callable[[], tuple[Path, str]] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Live Hardware Bridge")
        self.resize(700, 750)
        self._current_weapon = current_weapon
        self.client = BridgeClient(on_event=lambda text: self._logs.put(f"[device] {text}"))
        self._jobs: queue.Queue[Callable[[], None] | None] = queue.Queue()
        self._logs: queue.Queue[str] = queue.Queue()
        self._directory_results: queue.Queue[tuple[str, list[RemoteFile]]] = queue.Queue()
        self._progress_results: queue.Queue[tuple[int, int]] = queue.Queue()
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
                directory, entries = self._directory_results.get_nowait()
            except queue.Empty:
                break
            self.remote_directory.setText(directory)
            self.files.clear()
            for entry in sorted(entries, key=lambda item: (item.kind != FileType.DIRECTORY, item.path.lower())):
                name = entry.path.rsplit("/", 1)[-1]
                item = QTreeWidgetItem([name, "Folder" if entry.kind == FileType.DIRECTORY else "File",
                                        "" if entry.kind == FileType.DIRECTORY else f"{entry.size:,}"])
                item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
                self.files.addTopLevelItem(item)
        try:
            while True:
                current, total = self._progress_results.get_nowait()
                self.progress.setValue(round(100 * current / total) if total else 100)
        except queue.Empty:
            pass
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
        connect.clicked.connect(self._connect)
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

        layout.addWidget(QLabel("SD card file manager (LOCAL mode)"))
        self.remote_directory = QLineEdit("")
        self.remote_directory.setReadOnly(True)
        layout.addWidget(self.remote_directory)
        self.files = QTreeWidget()
        self.files.setHeaderLabels(["Name", "Type", "Bytes"])
        self.files.itemDoubleClicked.connect(self._open_remote_item)
        layout.addWidget(self.files)
        row = QHBoxLayout()
        for label, action in (("Up", self._up_directory), ("Refresh", self._refresh),
                              ("Upload", self._upload_files), ("Download", self._download_file)):
            button = QPushButton(label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        row = QHBoxLayout()
        for label, action in (("New folder", self._make_directory), ("Rename", self._rename_file),
                              ("Delete", self._delete_file), ("Sync folder", self._sync_directory)):
            button = QPushButton(label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

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

    def _connect(self) -> None:
        port = self.port.text().strip()
        def connect() -> None:
            self.client.connect(port)
            self._load_directory("")
        self._run("connected", connect)

    def _load_directory(self, remote: str) -> None:
        try:
            entries = self.client.list_directory(remote)
            self._directory_results.put((remote, entries))
        finally:
            self.client.release_storage()

    def _refresh(self) -> None:
        remote = self.remote_directory.text()
        self._run(f"listed /{remote}", lambda: self._load_directory(remote))

    def _open_remote_item(self, item: QTreeWidgetItem, column: int) -> None:
        if item.text(1) == "Folder":
            target = item.data(0, Qt.ItemDataRole.UserRole)
            self._run(f"listed /{target}", lambda: self._load_directory(target))

    def _up_directory(self) -> None:
        current = self.remote_directory.text()
        parent = current.rsplit("/", 1)[0] if "/" in current else ""
        self._run(f"listed /{parent}", lambda: self._load_directory(parent))

    def _selected_remote(self) -> str | None:
        item = self.files.currentItem()
        return str(item.data(0, Qt.ItemDataRole.UserRole)) if item else None

    def _report_progress(self, current: int, total: int) -> None:
        if current == total or current // (64 * 1024) != (current - 480) // (64 * 1024):
            self._progress_results.put((current, total))

    def _upload_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Upload files to blaster")
        if not files:
            return
        remote = self.remote_directory.text()
        def upload() -> None:
            try:
                for file in files:
                    local = Path(file)
                    destination = f"{remote}/{local.name}" if remote else local.name
                    self.client.deploy_file(local, destination, self._report_progress)
                self.client.activate()
            finally:
                self.client.release_storage()
            self._load_directory(remote)
        self._run(f"uploaded {len(files)} files", upload)

    def _download_file(self) -> None:
        remote = self._selected_remote()
        if not remote or (self.files.currentItem() and self.files.currentItem().text(1) != "File"):
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Download SD file", Path(remote).name)
        if not destination:
            return
        def download() -> None:
            try:
                self.client.download_file(remote, Path(destination), self._report_progress)
            finally:
                self.client.release_storage()
        self._run(f"downloaded {remote}", download)

    def _make_directory(self) -> None:
        name, ok = QInputDialog.getText(self, "New SD folder", "Folder name")
        if not ok or not name:
            return
        remote = self.remote_directory.text()
        path = f"{remote}/{name}" if remote else name
        def create() -> None:
            try:
                self.client.mkdir(path)
            finally:
                self.client.release_storage()
            self._load_directory(remote)
        self._run(f"created {path}", create)

    def _rename_file(self) -> None:
        remote = self._selected_remote()
        if not remote:
            return
        name, ok = QInputDialog.getText(self, "Rename SD file", "New name", text=Path(remote).name)
        if not ok or not name:
            return
        directory = self.remote_directory.text()
        destination = f"{directory}/{name}" if directory else name
        def rename() -> None:
            try:
                self.client.rename(remote, destination)
                self.client.activate()
            finally:
                self.client.release_storage()
            self._load_directory(directory)
        self._run(f"renamed {remote}", rename)

    def _delete_file(self) -> None:
        remote = self._selected_remote()
        if not remote:
            return
        if QMessageBox.question(self, "Delete SD entry", f"Permanently delete {remote}?") != QMessageBox.StandardButton.Yes:
            return
        directory = self.remote_directory.text()
        def delete() -> None:
            try:
                self.client.delete(remote)
                self.client.activate()
            finally:
                self.client.release_storage()
            self._load_directory(directory)
        self._run(f"deleted {remote}", delete)

    def _sync_directory(self) -> None:
        local = QFileDialog.getExistingDirectory(self, "Choose local directory to sync")
        if not local:
            return
        remote = self.remote_directory.text()
        def sync() -> None:
            def report(path: str, uploaded: bool) -> None:
                self._logs.put(("[upload] " if uploaded else "[unchanged] ") + path)
            uploaded, skipped = self.client.sync_tree(Path(local), remote, report)
            self._logs.put(f"Synced: {uploaded} uploaded, {skipped} unchanged")
            self._load_directory(remote)
        self._run("directory synchronized", sync)

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
                    path = asset.relative_to(root).as_posix()
                    changed = self.client.deploy_if_changed(asset, path)
                    self._logs.put(("[upload] " if changed else "[unchanged] ") + path)
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
