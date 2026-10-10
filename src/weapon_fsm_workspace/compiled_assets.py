"""Versioned little-endian SD formats shared with blaster-firmware/core.

All integer counts and UTF-8 string lengths are range-checked at export time.
Only the PC compiler parses YAML/JSON; runtime readers parse these binary files.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weapon_fsm_lights.infrastructure.loader import LightSequenceAsset

MANIFEST_MAGIC = b"WFMAN001"
SEQUENCE_MAGIC = b"WFLSEQ01"
LAYOUT_MAGIC = b"WFLLAY01"
VERSION = 1


class Writer:
    def __init__(self, magic: bytes) -> None:
        if len(magic) != 8:
            raise ValueError("Binary format magic must be eight bytes")
        self.data = bytearray(magic)
        self.u16(VERSION)

    def u8(self, value: int) -> None:
        self.data.extend(struct.pack("<B", value))

    def u16(self, value: int) -> None:
        self.data.extend(struct.pack("<H", value))

    def u32(self, value: int) -> None:
        self.data.extend(struct.pack("<I", value))

    def f32(self, value: float) -> None:
        if not math.isfinite(value):
            raise ValueError("Coordinates must be finite")
        self.data.extend(struct.pack("<f", value))

    def string(self, value: str) -> None:
        raw = value.encode("utf-8")
        self.u16(len(raw))
        self.data.extend(raw)

    def finish(self) -> bytes:
        return bytes(self.data)


def encode_manifest(banks: dict[str, list[str]]) -> bytes:
    writer = Writer(MANIFEST_MAGIC)
    writer.u16(len(banks))
    for bank_name, paths in banks.items():
        if not paths:
            raise ValueError(f"Bank {bank_name!r} cannot be empty")
        writer.string(bank_name)
        writer.u16(len(paths))
        for path in paths:
            if not path.endswith(".bin") or "\\" in path or path.startswith("/") or ".." in Path(path).parts:
                raise ValueError(f"Invalid binary weapon path: {path}")
            writer.string(path)
    return writer.finish()


def decode_manifest(data: bytes) -> dict[str, list[str]]:
    """Read an existing generated manifest to incrementally add weapon exports."""
    if not data.startswith(MANIFEST_MAGIC):
        raise ValueError("Unrecognized binary manifest")
    cursor = 8

    def u16() -> int:
        nonlocal cursor
        if cursor + 2 > len(data):
            raise ValueError("Truncated manifest")
        value = struct.unpack_from("<H", data, cursor)[0]
        cursor += 2
        return value

    def string() -> str:
        nonlocal cursor
        size = u16()
        if cursor + size > len(data):
            raise ValueError("Truncated manifest string")
        result = data[cursor:cursor + size].decode("utf-8")
        cursor += size
        return result

    if u16() != VERSION:
        raise ValueError("Unsupported manifest version")
    banks: dict[str, list[str]] = {}
    for _ in range(u16()):
        name = string()
        count = u16()
        if not count or name in banks:
            raise ValueError("Empty or duplicate bank")
        banks[name] = [string() for _ in range(count)]
    if cursor != len(data):
        raise ValueError("Trailing manifest data")
    return banks


def _color_bytes(color: str) -> tuple[int, int, int]:
    if len(color) != 7 or color[0] != "#":
        raise ValueError(f"Invalid RGB color: {color!r}")
    return tuple(bytes.fromhex(color[1:]))  # type: ignore[return-value]


def _led_indices(asset: LightSequenceAsset) -> dict[str, int]:
    ordered = sorted(asset.leds, key=lambda led: led.index if led.index is not None else 0)
    indices = {led.id: led.index if led.index is not None else i for i, led in enumerate(ordered)}
    if len(indices) != len(asset.leds) or len(set(indices.values())) != len(indices):
        raise ValueError("Light layout has duplicate LED IDs or indices")
    for index in indices.values():
        if index < 0 or index >= len(asset.leds):
            raise ValueError(f"Light LED index {index} is not contiguous in [0, {len(asset.leds)})")
    return indices


def encode_sequence(asset: LightSequenceAsset) -> bytes:
    indices = _led_indices(asset)
    writer = Writer(SEQUENCE_MAGIC)
    writer.u16(len(indices))
    writer.u32(len(asset.frames))
    writer.u32(sum(frame.duration_ms for frame in asset.frames))
    for frame in asset.frames:
        if frame.duration_ms <= 0:
            raise ValueError("Light frame duration must be positive")
        writer.u32(frame.duration_ms)
        writer.u16(len(frame.leds))
        for led_id, (color, intensity) in sorted(frame.leds.items(), key=lambda item: indices[item[0]]):
            if not math.isfinite(intensity) or not 0 <= intensity <= 1:
                raise ValueError(f"Invalid LED intensity {intensity}")
            writer.u16(indices[led_id])
            for channel in _color_bytes(color):
                writer.u8(channel)
            writer.u8(round(intensity * 255))
    return writer.finish()


def encode_layout(asset: LightSequenceAsset) -> bytes:
    indices = _led_indices(asset)
    writer = Writer(LAYOUT_MAGIC)
    writer.u16(len(indices))
    for led in sorted(asset.leds, key=lambda led: indices[led.id]):
        writer.u16(indices[led.id])
        writer.f32(led.x / asset.width if asset.width else 0.0)
        writer.f32(led.y / asset.height if asset.height else 0.0)
        writer.f32(led.radius / max(asset.width, asset.height, 1.0))
    return writer.finish()
