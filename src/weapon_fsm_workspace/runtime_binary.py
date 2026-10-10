from __future__ import annotations

import struct
from typing import Any


MAGIC = b"WFSMBIN1"
BINARY_VERSION = 1


class RuntimeBinaryWriter:
    def __init__(self) -> None:
        self._data = bytearray()

    def bytes(self) -> bytes:
        return bytes(self._data)

    def u8(self, value: int) -> None:
        self._data.extend(struct.pack("<B", value))

    def u16(self, value: int) -> None:
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f"Value does not fit in uint16: {value}")
        self._data.extend(struct.pack("<H", value))

    def i64(self, value: int) -> None:
        self._data.extend(struct.pack("<q", value))

    def f64(self, value: float) -> None:
        self._data.extend(struct.pack("<d", value))

    def string(self, value: str) -> None:
        encoded = value.encode("utf-8")
        self.u16(len(encoded))
        self._data.extend(encoded)

    def runtime_value(self, value: object) -> None:
        if value is None:
            self.u8(0)
        elif isinstance(value, bool):
            self.u8(1)
            self.u8(1 if value else 0)
        elif isinstance(value, int):
            self.u8(2)
            self.i64(value)
        elif isinstance(value, float):
            self.u8(3)
            self.f64(value)
        elif isinstance(value, str):
            self.u8(4)
            self.string(value)
        else:
            raise TypeError(f"Unsupported runtime value type: {type(value).__name__}")


def _write_comparison(writer: RuntimeBinaryWriter, comparison: dict[str, Any]) -> None:
    writer.string(str(comparison.get("name", "")))
    if "value" in comparison:
        writer.u8(1)
        writer.runtime_value(comparison["value"])
    elif comparison.get("value_from_var") is not None:
        writer.u8(2)
        writer.string(str(comparison["value_from_var"]))
    else:
        writer.u8(0)


def _write_guard(writer: RuntimeBinaryWriter, guard: dict[str, Any]) -> None:
    comparison_keys = ("var_eq", "var_gt", "var_gte", "var_lt", "var_lte")
    flags = 0
    if "trigger_pressed" in guard:
        flags |= 1 << 0
    for index, key in enumerate(comparison_keys, start=1):
        if guard.get(key) is not None:
            flags |= 1 << index
    writer.u8(flags)

    all_items = list(guard.get("all") or [])
    writer.u16(len(all_items))
    for item in all_items:
        _write_guard(writer, item)

    any_items = list(guard.get("any") or [])
    writer.u16(len(any_items))
    for item in any_items:
        _write_guard(writer, item)

    if flags & (1 << 0):
        writer.u8(1 if guard["trigger_pressed"] else 0)
    for index, key in enumerate(comparison_keys, start=1):
        if flags & (1 << index):
            _write_comparison(writer, guard[key])


_ACTION_FIELDS = (
    "clip",
    "clips",
    "mode",
    "interrupt",
    "effect",
    "clip_set",
    "sequence",
    "name",
    "value",
    "value_from_var",
    "delta",
    "event",
    "delay_ms",
    "delay_ms_from_var",
    "chance",
    "message",
)


def _write_action(writer: RuntimeBinaryWriter, action: dict[str, Any]) -> None:
    unknown = set(action) - {"type", *_ACTION_FIELDS}
    if unknown:
        raise ValueError(f"Unsupported runtime action fields: {sorted(unknown)}")

    writer.string(str(action.get("type", "")))
    flags = 0
    for index, key in enumerate(_ACTION_FIELDS):
        if key in action and action[key] is not None:
            flags |= 1 << index
    writer.u16(flags)

    if flags & (1 << 0):
        writer.string(str(action["clip"]))
    if flags & (1 << 1):
        clips = list(action["clips"])
        writer.u16(len(clips))
        for clip in clips:
            writer.string(str(clip))
    if flags & (1 << 2):
        writer.string(str(action["mode"]))
    if flags & (1 << 3):
        writer.string(str(action["interrupt"]))
    if flags & (1 << 4):
        writer.string(str(action["effect"]))
    if flags & (1 << 5):
        writer.string(str(action["clip_set"]))
    if flags & (1 << 6):
        writer.string(str(action["sequence"]))
    if flags & (1 << 7):
        writer.string(str(action["name"]))
    if flags & (1 << 8):
        writer.runtime_value(action["value"])
    if flags & (1 << 9):
        writer.string(str(action["value_from_var"]))
    if flags & (1 << 10):
        writer.i64(int(action["delta"]))
    if flags & (1 << 11):
        writer.string(str(action["event"]))
    if flags & (1 << 12):
        writer.i64(int(action["delay_ms"]))
    if flags & (1 << 13):
        writer.string(str(action["delay_ms_from_var"]))
    if flags & (1 << 14):
        writer.f64(float(action["chance"]))
    if flags & (1 << 15):
        writer.string(str(action["message"]))


def _write_actions(writer: RuntimeBinaryWriter, actions: list[dict[str, Any]]) -> None:
    writer.u16(len(actions))
    for action in actions:
        _write_action(writer, action)


def encode_runtime(payload: dict[str, Any]) -> bytes:
    """Encode the editor runtime payload without constructing a JSON document on the MCU."""
    writer = RuntimeBinaryWriter()
    writer._data.extend(MAGIC)
    writer.u16(BINARY_VERSION)
    writer.string(str(payload.get("initial_state", "ready")))

    clips = payload.get("clips") or {}
    writer.u16(len(clips))
    for name, clip in clips.items():
        writer.string(str(name))
        writer.string(str(clip.get("path", "")))
        writer.u8(1 if clip.get("preload", True) else 0)

    clip_sets = payload.get("clip_sets") or {}
    writer.u16(len(clip_sets))
    for name, clip_set in clip_sets.items():
        writer.string(str(name))
        writer.string(str(clip_set.get("mode", "random")))
        values = list(clip_set.get("clips") or [])
        writer.u16(len(values))
        for clip in values:
            writer.string(str(clip))

    effects = payload.get("audio_effects") or {}
    writer.u16(len(effects))
    for name, effect in effects.items():
        writer.string(str(name))
        writer.string(str(effect.get("mode", "once")))
        writer.string(str(effect.get("interrupt", "interrupt")))
        writer.u8(1 if effect.get("loop", False) else 0)
        writer.f64(float(effect.get("gain", 1.0)))
        values = list(effect.get("clips") or [])
        writer.u16(len(values))
        for clip in values:
            writer.string(str(clip))

    sequences = payload.get("light_sequences") or {}
    writer.u16(len(sequences))
    for name, sequence in sequences.items():
        writer.string(str(name))
        writer.string(str(sequence.get("path", "")))
        writer.u8(1 if sequence.get("preload", True) else 0)

    variables = payload.get("variables") or {}
    writer.u16(len(variables))
    for name, value in variables.items():
        writer.string(str(name))
        writer.runtime_value(value)

    states = list(payload.get("states") or [])
    writer.u16(len(states))
    for state in states:
        writer.string(str(state.get("id", "")))
        writer.string(str(state.get("label", state.get("id", ""))))
        _write_actions(writer, list(state.get("on_entry") or []))
        _write_actions(writer, list(state.get("on_exit") or []))

    transitions = list(payload.get("transitions") or [])
    writer.u16(len(transitions))
    for transition in transitions:
        writer.string(str(transition.get("id", "")))
        writer.string(str(transition.get("source", "")))
        writer.string(str(transition.get("trigger", "")))
        writer.string(str(transition.get("target", "")))
        writer.u8(1 if transition.get("internal", False) else 0)
        guard = transition.get("guard")
        writer.u8(1 if guard is not None else 0)
        if guard is not None:
            _write_guard(writer, guard)
        _write_actions(writer, list(transition.get("actions") or []))

    return writer.bytes()
