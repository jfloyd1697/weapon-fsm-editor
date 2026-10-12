"""Dependency-light binary format tests; these also generate firmware C++ fixtures."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from weapon_fsm_workspace.compiled_assets import (
    LAYOUT_MAGIC, MANIFEST_MAGIC, SEQUENCE_MAGIC,
    decode_manifest, encode_layout, encode_manifest, encode_sequence,
)


@dataclass(frozen=True)
class Led:
    id: str
    index: int
    x: float = 0.5
    y: float = 0.5
    radius: float = 0.1


@dataclass(frozen=True)
class Frame:
    duration_ms: int
    leds: dict[str, tuple[str, float]]


@dataclass(frozen=True)
class Asset:
    width: float
    height: float
    leds: tuple[Led, ...]
    frames: tuple[Frame, ...]


def sample() -> Asset:
    return Asset(1.0, 1.0, (Led("0", 0), Led("1", 1)), (
        Frame(100, {"1": ("#00ff00", 1.0)}),
        Frame(200, {"0": ("#ff0000", 0.5)}),
    ))


def test_manifest_roundtrip() -> None:
    encoded = encode_manifest({"Default": ["Default/test/weapon.bin"]})
    assert encoded.startswith(MANIFEST_MAGIC)
    assert decode_manifest(encoded) == {"Default": ["Default/test/weapon.bin"]}
    with pytest.raises(ValueError):
        decode_manifest(encoded[:-1])
    with pytest.raises(ValueError):
        encode_manifest({"Default": ["../weapon.bin"]})
    with pytest.raises(ValueError):
        encode_manifest({"Default": ["Default/test/weapon.json"]})


def test_sequence_and_layout() -> None:
    sequence = encode_sequence(sample())
    layout = encode_layout(sample())
    assert sequence[:8] == SEQUENCE_MAGIC
    assert sequence[8:12] == b"\x01\x00\x02\x00"  # version and 2 LEDs
    assert sequence[12:20] == b"\x02\x00\x00\x00\x2c\x01\x00\x00"  # 2 frames, 300ms
    assert layout[:8] == LAYOUT_MAGIC
    assert len(layout) == 12 + 2 * 14


def test_invalid_sequence_data() -> None:
    with pytest.raises(ValueError):
        encode_sequence(Asset(1, 1, (Led("0", 0),), (Frame(0, {}),)))
    with pytest.raises(ValueError):
        encode_sequence(Asset(1, 1, (Led("0", 0),), (Frame(100, {"0": ("#gggggg", 1)}),)))
    with pytest.raises(ValueError):
        encode_layout(Asset(1, 1, (Led("0", 0), Led("1", 0)), ()))
