"""Binary serial bridge. The client never executes device I/O on a Qt timer callback."""
from __future__ import annotations

import enum
import os
import tempfile
import queue
import struct
import threading
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class BridgeMode(enum.IntEnum):
    LOCAL = 0
    REMOTE_INPUT = 1
    REMOTE_CONTROL = 2


class BridgeOp(enum.IntEnum):
    HELLO = 1
    SET_MODE = 2
    HEARTBEAT = 3
    INPUT = 4
    PLAY_AUDIO = 5
    STOP_AUDIO = 6
    PLAY_LIGHT = 7
    STOP_LIGHT = 8
    LED_FRAME = 9
    FILE_BEGIN = 10
    FILE_CHUNK = 11
    FILE_COMMIT = 12
    STATUS = 13
    ACTIVATE = 14
    FILE_LIST = 15
    FILE_STAT = 16
    FILE_READ = 17
    FILE_DELETE = 18
    FILE_MKDIR = 19
    FILE_RENAME = 20
    FILE_ABORT = 21
    FILE_HASH = 22
    FILE_RELEASE = 23
    ACK = 128
    EVENT = 129


class ProtocolError(RuntimeError):
    pass


class FileType(enum.IntEnum):
    MISSING = 0
    FILE = 1
    DIRECTORY = 2


@dataclass(frozen=True)
class RemoteFile:
    path: str
    kind: FileType
    size: int


_MAX_REMOTE_PATH_BYTES = 180
_TRANSFER_CHUNK_BYTES = 480
_HASH_TIMEOUT_S = 180.0
_STATUS_NAMES = {
    1: "Invalid request or path",
    2: "File or directory not found",
    3: "SD card I/O failure",
    4: "Device busy / existing temporary file",
    5: "Invalid bridge mode",
    6: "CRC32 verification failed",
}


def _remote_path(path: str, *, allow_root: bool = False) -> bytes:
    if not path and allow_root:
        return b""
    try:
        encoded = path.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("Device paths must be ASCII") from exc
    if len(encoded) > _MAX_REMOTE_PATH_BYTES or path.startswith("/") or path.endswith("/"):
        raise ValueError(f"Invalid device path: {path!r}")
    segments = path.split("/")
    if any(not part or part in (".", "..") or part.endswith((".upload", ".backup"))
           for part in segments):
        raise ValueError(f"Invalid device path: {path!r}")
    if any(ord(ch) < 33 or ord(ch) > 126 or ch in '\\:*?"<>|' for ch in path):
        raise ValueError(f"Invalid device path: {path!r}")
    return encoded


def _crc32_file(path: Path) -> int:
    value = 0
    with path.open("rb") as handle:
        while chunk := handle.read(64 * 1024):
            value = zlib.crc32(chunk, value)
    return value



def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xFFFF
    return crc


def encode_frame(op: BridgeOp, sequence: int, payload: bytes = b"") -> bytes:
    if len(payload) > 512:
        raise ValueError("Bridge payload exceeds 512 bytes")
    body = struct.pack("<HBH", len(payload), op, sequence & 0xFFFF) + payload
    return b"\xA5\x5A" + body + struct.pack("<H", crc16(body))


@dataclass(frozen=True)
class Frame:
    op: BridgeOp
    sequence: int
    payload: bytes


class FrameParser:
    """Incremental bounded parser, tolerant of plain-text debug output."""
    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        self.buffer.extend(data)
        result: list[Frame] = []
        while True:
            start = self.buffer.find(b"\xA5\x5A")
            if start < 0:
                self.buffer[:] = self.buffer[-1:] if self.buffer.endswith(b"\xA5") else b""
                break
            if start:
                del self.buffer[:start]
            if len(self.buffer) < 9:
                break
            length = struct.unpack_from("<H", self.buffer, 2)[0]
            if length > 512:
                del self.buffer[0]
                continue
            size = length + 9
            if len(self.buffer) < size:
                break
            body = self.buffer[2:size - 2]
            expected = struct.unpack_from("<H", self.buffer, size - 2)[0]
            if crc16(body) != expected:
                del self.buffer[0]
                continue
            try:
                op = BridgeOp(self.buffer[4])
            except ValueError:
                del self.buffer[:size]
                continue
            seq = struct.unpack_from("<H", self.buffer, 5)[0]
            result.append(Frame(op, seq, bytes(self.buffer[7:size - 2])))
            del self.buffer[:size]
        return result


class BridgeClient:
    """Thread-safe serial client with acknowledgments and heartbeat.

    Uses one reader thread so blocking SD deployment cannot starve replies.
    pyserial is imported only when connect() is called.
    """
    def __init__(self, on_event: Callable[[str], None] | None = None) -> None:
        self.on_event = on_event
        self.serial = None
        self._reader: threading.Thread | None = None
        self._alive = threading.Event()
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._responses: dict[int, queue.Queue[Frame]] = {}
        self._sequence = 0
        self._parser = FrameParser()
        self.mode = BridgeMode.LOCAL
        self._last_heartbeat = time.monotonic()
        self._storage_active = False

    def connect(self, port: str, baudrate: int = 115200) -> None:
        if self.serial is not None:
            raise ProtocolError("Already connected; disconnect before connecting again")
        import serial  # type: ignore[import-untyped]
        self.serial = serial.Serial(port, baudrate=baudrate, timeout=0.05, write_timeout=2)
        self._alive.set()
        self._reader = threading.Thread(target=self._read_loop, name="blaster-serial", daemon=True)
        self._reader.start()
        response = self.command(BridgeOp.HELLO, expected=BridgeOp.STATUS)
        if not response.payload or response.payload[0] != 2:
            self.close()
            raise ProtocolError("Firmware does not support SD bridge protocol v2")

    def close(self) -> None:
        if self.serial and self.serial.is_open and self._alive.is_set():
            try:
                if self._storage_active:
                    self.command(BridgeOp.FILE_ABORT)
                    self.release_storage()
                if self.mode != BridgeMode.LOCAL:
                    self.set_mode(BridgeMode.LOCAL)
            except (OSError, ProtocolError):
                pass
        self._alive.clear()
        if self._reader and self._reader is not threading.current_thread():
            self._reader.join(timeout=1)
        if self.serial:
            self.serial.close()
            self.serial = None
        self._reader = None
        self.mode = BridgeMode.LOCAL
        self._storage_active = False

    def _read_loop(self) -> None:
        try:
            while self._alive.is_set() and self.serial is not None:
                data = self.serial.read(256)
                for frame in self._parser.feed(data):
                    if frame.op == BridgeOp.EVENT:
                        if self.on_event:
                            self.on_event(frame.payload.decode("utf-8", errors="replace"))
                    else:
                        with self._lock:
                            waiter = self._responses.get(frame.sequence)
                        if waiter:
                            waiter.put(frame)
                if (self.mode != BridgeMode.LOCAL or self._storage_active) and time.monotonic() - self._last_heartbeat >= 0.5:
                    self._send_heartbeat()
        finally:
            self._alive.clear()

    def _send_heartbeat(self) -> None:
        self._last_heartbeat = time.monotonic()
        if self.serial:
            with self._write_lock:
                self.serial.write(encode_frame(BridgeOp.HEARTBEAT, 0))

    def command(self, op: BridgeOp, payload: bytes = b"", *, expected: BridgeOp = BridgeOp.ACK,
                timeout: float = 5.0) -> Frame:
        if not self.serial or not self._alive.is_set():
            raise ProtocolError("Not connected")
        with self._lock:
            self._sequence = (self._sequence + 1) & 0xFFFF
            if self._sequence == 0:
                self._sequence = 1
            seq = self._sequence
            waiter: queue.Queue[Frame] = queue.Queue(maxsize=1)
            self._responses[seq] = waiter
        try:
            with self._write_lock:
                self.serial.write(encode_frame(op, seq, payload))
            try:
                response = waiter.get(timeout=timeout)
            except queue.Empty as exc:
                raise ProtocolError(f"Timeout waiting for {op.name} acknowledgment") from exc
            if response.op != expected:
                raise ProtocolError(f"Unexpected response {response.op}")
            if expected == BridgeOp.ACK:
                if not response.payload or response.payload[0] != 0:
                    status = response.payload[0] if response.payload else -1
                    raise ProtocolError(f"{op.name}: {_STATUS_NAMES.get(status, f'error {status}')}")
            return response
        finally:
            with self._lock:
                self._responses.pop(seq, None)

    def set_mode(self, mode: BridgeMode) -> None:
        self.command(BridgeOp.SET_MODE, bytes([mode]))
        self.mode = mode
        self._last_heartbeat = time.monotonic()

    def input(self, button: int, pressed: bool) -> None:
        self.command(BridgeOp.INPUT, bytes((button, int(pressed))))

    def tap_reload(self, hold_s: float = 0.06) -> None:
        self.input(3, True)
        try:
            time.sleep(hold_s)
        finally:
            self.input(3, False)

    def play_audio(self, path: str, loop: bool = False) -> None:
        self.command(BridgeOp.PLAY_AUDIO, bytes([int(loop)]) + path.encode())

    def stop_audio(self) -> None:
        self.command(BridgeOp.STOP_AUDIO)

    def play_light(self, path: str, loop: bool = False) -> None:
        self.command(BridgeOp.PLAY_LIGHT, bytes([int(loop)]) + path.encode())

    def stop_light(self) -> None:
        self.command(BridgeOp.STOP_LIGHT)

    def led_frame(self, rgb: bytes) -> None:
        if not rgb or len(rgb) % 3 or len(rgb) > 384:
            raise ValueError("Expected 1–128 RGB pixels")
        self.command(BridgeOp.LED_FRAME, struct.pack("<H", len(rgb)//3) + rgb)

    def _file_command(self, op: BridgeOp, payload: bytes = b"", *, timeout: float = 5.0) -> bytes:
        if self.mode != BridgeMode.LOCAL:
            raise ProtocolError("SD card operations require LOCAL mode")
        self._storage_active = True
        return self.command(op, payload, timeout=timeout).payload[1:]

    def list_directory(self, remote_dir: str = "") -> list[RemoteFile]:
        path = _remote_path(remote_dir, allow_root=True)
        result: list[RemoteFile] = []
        offset = 0
        while True:
            page = self._file_command(BridgeOp.FILE_LIST, struct.pack("<H", offset) + path)
            if len(page) < 3:
                raise ProtocolError("Malformed directory listing")
            more, next_offset = struct.unpack_from("<BH", page)
            position = 3
            while position < len(page):
                if len(page) - position < 6:
                    raise ProtocolError("Truncated directory entry")
                kind, size, length = struct.unpack_from("<BIB", page, position)
                position += 6
                if len(page) - position < length:
                    raise ProtocolError("Truncated directory name")
                name = page[position:position + length].decode("ascii")
                position += length
                result.append(RemoteFile(f"{remote_dir}/{name}" if remote_dir else name,
                                         FileType(kind), size))
            if not more:
                return result
            if next_offset <= offset:
                raise ProtocolError("Directory pagination did not advance")
            offset = next_offset

    def stat(self, path: str) -> RemoteFile:
        data = self._file_command(BridgeOp.FILE_STAT, _remote_path(path))
        if len(data) != 5:
            raise ProtocolError("Malformed file stat response")
        kind, size = struct.unpack("<BI", data)
        return RemoteFile(path, FileType(kind), size)

    def remote_checksum(self, path: str) -> tuple[int, int]:
        data = self._file_command(BridgeOp.FILE_HASH, _remote_path(path), timeout=_HASH_TIMEOUT_S)
        if len(data) != 8:
            raise ProtocolError("Malformed file checksum response")
        return struct.unpack("<II", data)

    def mkdir(self, path: str) -> None:
        self._file_command(BridgeOp.FILE_MKDIR, _remote_path(path))

    def delete(self, path: str) -> None:
        self._file_command(BridgeOp.FILE_DELETE, _remote_path(path))

    def rename(self, source: str, destination: str) -> None:
        payload = _remote_path(source) + b"\0" + _remote_path(destination)
        self._file_command(BridgeOp.FILE_RENAME, payload)

    def deploy_file(self, local: Path, remote: str,
                    progress: Callable[[int, int], None] | None = None) -> None:
        path = _remote_path(remote)
        size = local.stat().st_size
        if size > 0xFFFFFFFF:
            raise ValueError("SD filesystem supports files up to 4 GiB")
        self._file_command(BridgeOp.FILE_BEGIN, struct.pack("<I", size) + path)
        checksum = 0
        total = 0
        try:
            with local.open("rb") as handle:
                while data := handle.read(_TRANSFER_CHUNK_BYTES):
                    self._file_command(BridgeOp.FILE_CHUNK, data)
                    checksum = zlib.crc32(data, checksum)
                    total += len(data)
                    if progress:
                        progress(total, size)
            self._file_command(BridgeOp.FILE_COMMIT, struct.pack("<I", checksum))
        except Exception:
            try:
                self._file_command(BridgeOp.FILE_ABORT)
            except (ProtocolError, OSError):
                pass
            raise

    def deploy_if_changed(self, local: Path, remote: str) -> bool:
        """Return True when a file was uploaded, False when the SD copy is identical."""
        old = self.stat(remote)
        if old.kind == FileType.FILE and old.size == local.stat().st_size:
            size, crc = self.remote_checksum(remote)
            if size == old.size and crc == _crc32_file(local):
                return False
        self.deploy_file(local, remote)
        return True

    def download_file(self, remote: str, local: Path,
                      progress: Callable[[int, int], None] | None = None) -> None:
        path = _remote_path(remote)
        file = self.stat(remote)
        if file.kind != FileType.FILE:
            raise ProtocolError(f"Not a file: {remote}")
        local.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=local.parent, prefix=local.name + ".",
                                         suffix=".download", delete=False) as handle:
            temporary = Path(handle.name)
        try:
            with temporary.open("wb") as handle:
                offset = 0
                while offset < file.size:
                    amount = min(128, file.size - offset)
                    chunk = self._file_command(
                        BridgeOp.FILE_READ, struct.pack("<IH", offset, amount) + path)
                    if not chunk or len(chunk) > amount:
                        raise ProtocolError(f"Unexpected end of SD file: {remote}")
                    handle.write(chunk)
                    offset += len(chunk)
                    if progress:
                        progress(offset, file.size)
            remote_size, remote_crc = self.remote_checksum(remote)
            if remote_size != file.size or remote_crc != _crc32_file(temporary):
                raise ProtocolError(f"Checksum mismatch downloading {remote}")
            os.replace(temporary, local)
        finally:
            temporary.unlink(missing_ok=True)

    def release_storage(self) -> None:
        if self._storage_active:
            self.command(BridgeOp.FILE_RELEASE)
            self._storage_active = False

    def activate(self) -> None:
        """Commit deployment and rebuild the MCU weapon bank index."""
        self.command(BridgeOp.ACTIVATE)
        self._storage_active = False

    def sync_tree(self, local_root: Path, prefix: str = "",
                  progress: Callable[[str, bool], None] | None = None,
                  *, activate: bool = True) -> tuple[int, int]:
        """Compare size and CRC32, transfer changed files only. Never delete unrelated SD files."""
        uploaded = skipped = 0
        try:
            for local in sorted(local_root.rglob("*")):
                if not local.is_file():
                    continue
                relative = local.relative_to(local_root).as_posix()
                remote = f"{prefix.rstrip('/')}/{relative}" if prefix else relative
                changed = self.deploy_if_changed(local, remote)
                if changed:
                    uploaded += 1
                else:
                    skipped += 1
                if progress:
                    progress(remote, changed)
            if activate:
                self.activate()
            else:
                self.release_storage()
            return uploaded, skipped
        except Exception:
            self.release_storage()
            raise

    def deploy_tree(self, local_root: Path, prefix: str = "assets") -> None:
        self.sync_tree(local_root, prefix)
