"""End-to-end PC transport tests against an in-memory protocol-v2 device."""
from __future__ import annotations

import queue
import struct
import threading
import zlib
from pathlib import Path

import pytest

from weapon_fsm_workspace.hardware_bridge.client import (
    BridgeClient, BridgeOp, FileType, FrameParser, ProtocolError, encode_frame,
)


class MemoryDevice:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.folders: set[str] = {""}
        self.transfer: tuple[str, int, bytearray] | None = None
        self.uploads = 0
        self.activations = 0
        self.released = 0
        self.is_open = True
        self.responses: queue.Queue[bytes] = queue.Queue()
        self.parser = FrameParser()

    def read(self, size: int) -> bytes:
        try:
            return self.responses.get(timeout=0.02)
        except queue.Empty:
            return b""

    def write(self, data: bytes) -> int:
        for frame in self.parser.feed(data):
            if frame.sequence == 0:
                continue
            response = self.process(frame.op, frame.payload)
            if frame.op == BridgeOp.HELLO:
                self.responses.put(encode_frame(BridgeOp.STATUS, frame.sequence, b"\x02STM32F411 SD"))
            else:
                self.responses.put(encode_frame(BridgeOp.ACK, frame.sequence, response))
        return len(data)

    def process(self, op: BridgeOp, data: bytes) -> bytes:
        if op == BridgeOp.FILE_STAT:
            path = data.decode()
            kind = 1 if path in self.files else 2 if path in self.folders else 0
            return b"\0" + struct.pack("<BI", kind, len(self.files.get(path, b"")))
        if op == BridgeOp.FILE_LIST:
            start = struct.unpack_from("<H", data)[0]
            path = data[2:].decode()
            if path not in self.folders:
                return b"\x02"
            prefix = path + "/" if path else ""
            entries = []
            for file in sorted(self.files):
                if file.startswith(prefix) and "/" not in file[len(prefix):]:
                    entries.append((file[len(prefix):], 1, len(self.files[file])))
            for folder in sorted(self.folders):
                if folder.startswith(prefix) and folder != path and "/" not in folder[len(prefix):]:
                    entries.append((folder[len(prefix):], 2, 0))
            page = bytearray(struct.pack("<BH", 0, len(entries)))
            for name, kind, size in entries[start:]:
                encoded = name.encode()
                page += struct.pack("<BIB", kind, size, len(encoded)) + encoded
            return b"\0" + page
        if op == BridgeOp.FILE_HASH:
            content = self.files.get(data.decode())
            return b"\x02" if content is None else b"\0" + struct.pack(
                "<II", len(content), zlib.crc32(content))
        if op == BridgeOp.FILE_READ:
            offset, count = struct.unpack_from("<IH", data)
            path = data[6:].decode()
            return b"\0" + self.files[path][offset:offset + count]
        if op == BridgeOp.FILE_BEGIN:
            size = struct.unpack_from("<I", data)[0]
            path = data[4:].decode()
            self.transfer = (path, size, bytearray())
            return b"\0"
        if op == BridgeOp.FILE_CHUNK:
            assert self.transfer
            self.transfer[2].extend(data)
            return b"\0"
        if op == BridgeOp.FILE_COMMIT:
            assert self.transfer
            path, expected_size, buffer = self.transfer
            if len(buffer) != expected_size or zlib.crc32(buffer) != struct.unpack("<I", data)[0]:
                return b"\x06"
            self.files[path] = bytes(buffer)
            self.folders.update("/".join(path.split("/")[:i]) for i in range(1, len(path.split("/"))))
            self.transfer = None
            self.uploads += 1
            return b"\0"
        if op == BridgeOp.FILE_ABORT:
            self.transfer = None
            return b"\0"
        if op == BridgeOp.FILE_DELETE:
            path = data.decode()
            if path in self.files:
                del self.files[path]
            else:
                self.folders.remove(path)
            return b"\0"
        if op == BridgeOp.FILE_MKDIR:
            path = data.decode()
            self.folders.update("/".join(path.split("/")[:i]) for i in range(1, len(path.split("/")) + 1))
            return b"\0"
        if op == BridgeOp.FILE_RENAME:
            src, dst = data.decode().split("\0")
            self.files[dst] = self.files.pop(src)
            return b"\0"
        if op == BridgeOp.FILE_RELEASE:
            self.released += 1
            return b"\0"
        if op == BridgeOp.ACTIVATE:
            self.activations += 1
            return b"\0"
        return b"\0"

    def close(self) -> None:
        self.is_open = False


@pytest.fixture
def connection():
    device = MemoryDevice()
    client = BridgeClient()
    client.serial = device
    client._alive.set()
    client._reader = threading.Thread(target=client._read_loop, daemon=True)
    client._reader.start()
    yield client, device
    client.close()


def test_sync_skips_unchanged_by_crc_not_size(connection, tmp_path):
    client, device = connection
    root = tmp_path / "assets"
    (root / "weapons").mkdir(parents=True)
    (root / "weapons" / "weapon.bin").write_bytes(b"compiled-weapon")
    (root / "weapons" / "audio.wav").write_bytes(b"audio" * 100)
    assert client.sync_tree(root, "assets") == (2, 0)
    assert client.sync_tree(root, "assets") == (0, 2)
    assert device.uploads == 2
    (root / "weapons" / "audio.wav").write_bytes(b"AUDIO" * 100)
    assert client.sync_tree(root, "assets") == (1, 1)
    assert device.files["assets/weapons/audio.wav"] == b"AUDIO" * 100
    assert device.activations == 3


def test_download_crc_and_operations(connection, tmp_path):
    client, device = connection
    client.mkdir("assets/weapons")
    local = tmp_path / "source.bin"
    local.write_bytes(bytes(range(256)) * 3)
    client.deploy_file(local, "assets/weapons/source.bin")
    assert client.stat("assets/weapons/source.bin").kind == FileType.FILE
    assert len(client.list_directory("assets/weapons")) == 1
    destination = tmp_path / "download.bin"
    client.download_file("assets/weapons/source.bin", destination)
    assert destination.read_bytes() == local.read_bytes()
    client.rename("assets/weapons/source.bin", "assets/weapons/renamed.bin")
    client.delete("assets/weapons/renamed.bin")
    assert client.stat("assets/weapons/renamed.bin").kind == FileType.MISSING
    client.release_storage()
    assert device.released == 1


@pytest.mark.parametrize("path", ["../bad", "/absolute", "assets//double", "a\\b", "x.upload", "a:drive"])
def test_untrusted_paths_rejected(connection, tmp_path, path):
    client, _ = connection
    file = tmp_path / "asset"
    file.write_bytes(b"test")
    with pytest.raises(ValueError):
        client.deploy_file(file, path)
