"""Binary serial bridge. The client never executes device I/O on a Qt timer callback."""
from __future__ import annotations

import enum
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
    ACK = 128
    EVENT = 129


class ProtocolError(RuntimeError):
    pass


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

    def connect(self, port: str, baudrate: int = 115200) -> None:
        import serial  # type: ignore[import-untyped]
        self.serial = serial.Serial(port, baudrate=baudrate, timeout=0.05, write_timeout=2)
        self._alive.set()
        self._reader = threading.Thread(target=self._read_loop, name="blaster-serial", daemon=True)
        self._reader.start()
        self.command(BridgeOp.HELLO, expected=BridgeOp.STATUS)

    def close(self) -> None:
        if self.serial and self.serial.is_open:
            try:
                self.set_mode(BridgeMode.LOCAL)
            except (OSError, ProtocolError):
                pass
        self._alive.clear()
        if self._reader and self._reader is not threading.current_thread():
            self._reader.join(timeout=1)
        if self.serial:
            self.serial.close()
            self.serial = None
        self.mode = BridgeMode.LOCAL

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
                if self.mode != BridgeMode.LOCAL and time.monotonic() - self._last_heartbeat >= 0.5:
                    self._send_heartbeat()
        finally:
            self._alive.clear()

    def _send_heartbeat(self) -> None:
        self._last_heartbeat = time.monotonic()
        if self.serial:
            with self._write_lock:
                self.serial.write(encode_frame(BridgeOp.HEARTBEAT, 0))

    def command(self, op: BridgeOp, payload: bytes = b"", *, expected: BridgeOp = BridgeOp.ACK) -> Frame:
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
                response = waiter.get(timeout=3.0)
            except queue.Empty as exc:
                raise ProtocolError(f"Timeout waiting for {op.name} acknowledgment") from exc
            if response.op != expected:
                raise ProtocolError(f"Unexpected response {response.op}")
            if expected == BridgeOp.ACK and response.payload != b"\x00":
                raise ProtocolError(f"{op.name} rejected (status {response.payload.hex()})")
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

    def deploy_file(self, local: Path, remote: str) -> None:
        if self.mode != BridgeMode.LOCAL:
            raise ProtocolError("Deployment requires LOCAL mode")
        if local.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("File too large for bridge")
        path = remote.encode()
        if not path or len(path) > 500:
            raise ValueError("Invalid remote path")
        self.command(BridgeOp.FILE_BEGIN, struct.pack("<I", local.stat().st_size) + path)
        crc = 0
        with local.open("rb") as handle:
            while data := handle.read(480):
                crc = zlib.crc32(data, crc)
                self.command(BridgeOp.FILE_CHUNK, data)
        self.command(BridgeOp.FILE_COMMIT, struct.pack("<I", crc))

    def activate(self) -> None:
        """Reload the bank index and active weapon after successful SD deployment."""
        self.command(BridgeOp.ACTIVATE)

    def deploy_tree(self, local_root: Path, prefix: str = "assets") -> None:
        for path in sorted(local_root.rglob("*")):
            if path.is_file():
                self.deploy_file(path, (Path(prefix) / path.relative_to(local_root)).as_posix())
        self.activate()
