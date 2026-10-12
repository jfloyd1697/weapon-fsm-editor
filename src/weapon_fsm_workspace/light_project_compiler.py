"""Compile authored light-project animation layers without GUI dependencies.

Keep formulas consistent with weapon_fsm_lights.domain.compiler; this module is
used only for bulk export in minimal environments where the GUI is not installed.
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from types import SimpleNamespace

import yaml


def compile_animation_project(source: Path, name: str, leds: tuple[SimpleNamespace, ...]):
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    animation = document["animations"][name]
    frame_ms = int(animation["frame_duration_ms"])
    duration_ms = int(animation["duration_ms"])
    if frame_ms <= 0 or duration_ms <= 0 or not animation.get("layers"):
        raise ValueError(f"Invalid authored animation {name!r}")
    frames = []
    for time_ms in range(0, duration_ms, frame_ms):
        colors = {}
        for led in leds:
            brightest = ("#202020", 0.0)
            for layer in animation["layers"]:
                if time_ms < layer.get("start_ms", 0):
                    continue
                t = time_ms - int(layer.get("start_ms", 0))
                duration = max(1, int(layer["duration_ms"]))
                if t > duration:
                    continue
                progress = t / duration
                color = str(layer["color"])
                intensity = float(layer["intensity"])
                kind = layer["type"]
                if kind == "solid":
                    value = intensity
                elif kind == "radial_pulse":
                    x, y = layer.get("center", [0.5, 0.5])
                    radius = math.hypot(led.x - x, led.y - y)
                    active = float(layer["radius_from"]) + (
                        float(layer["radius_to"]) - float(layer["radius_from"])
                    ) * progress
                    value = max(0.0, 1 - abs(radius - active) / max(.0001, float(layer["width"]) / 2)) * intensity
                elif kind == "wipe":
                    dx, dy = layer["direction"]
                    length = math.hypot(dx, dy) or 1
                    position = (led.x * dx + led.y * dy) / length
                    active = progress * float(layer["speed"])
                    value = max(0.0, 1 - abs(position - active) / max(.0001, float(layer["width"]) / 2)) * intensity
                elif kind == "blink":
                    speed = max(0.0, float(layer["speed"]))
                    phase = (progress * speed) % 1 if speed else progress
                    value = intensity if phase < .5 else 0.0
                elif kind == "chase":
                    position = (progress * float(layer["speed"])) % 1
                    led_position = (led.index % 1000) / 1000
                    distance = abs(led_position - position)
                    distance = min(distance, 1 - distance)
                    value = max(0.0, 1 - distance / max(.0001, float(layer["width"]) / 2)) * intensity
                elif kind == "sparkle":
                    bucket = time_ms // max(1, int(100 / max(.01, float(layer["speed"]))))
                    enabled = random.Random(int(layer["seed"]) + led.index * 131 + bucket * 17).random()
                    value = intensity if enabled < float(layer["density"]) else 0.0
                else:
                    raise ValueError(f"Unknown lighting layer type {kind!r} in {name}")
                if value >= brightest[1]:
                    brightest = (color, min(1.0, max(0.0, value)))
            if brightest[1] > 0:
                colors[led.id] = brightest
        frames.append(SimpleNamespace(duration_ms=min(frame_ms, duration_ms - time_ms), leds=colors))
    return SimpleNamespace(width=1.0, height=1.0, leds=leds, frames=tuple(frames))
