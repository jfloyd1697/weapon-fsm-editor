from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from weapon_fsm_lights import LightFrame, LightSequenceAsset, load_light_sequence


@dataclass(frozen=True)
class NamedLightAnimation:
    name: str
    asset: LightSequenceAsset
    source_path: Path


def load_light_animations(path: str | Path) -> list[NamedLightAnimation]:
    """Load either a normal light sequence YAML/JSON or a multi-animation YAML.

    Supported single sequence shape is the existing weapon_fsm_lights format:

        layout:
          leds: [...]
        frames: [...]

    Supported multi-animation shape:

        layout:
          ...
        animations:
          charge_glow:
            frame_duration_ms: 80
            frames: [...]
          muzzle_flash:
            frames: [...]
    """

    source_path = Path(path).expanduser().resolve()
    data = _load_yaml(source_path)

    animations = data.get("animations")
    if not animations:
        asset = load_light_sequence(source_path)
        return [NamedLightAnimation(source_path.stem, asset, source_path)]

    base_layout = _load_base_layout_asset(data, source_path)
    animation_items = _animation_items(animations)

    result: list[NamedLightAnimation] = []
    for name, raw_animation in animation_items:
        if not isinstance(raw_animation, dict):
            raise ValueError(f"Animation '{name}' must be a mapping")

        frame_duration_ms = int(
            raw_animation.get(
                "frame_duration_ms",
                data.get("frame_duration_ms", 100),
            )
        )
        frames = _parse_frames(raw_animation.get("frames", []), frame_duration_ms)
        if not frames:
            frames = [LightFrame(duration_ms=frame_duration_ms, leds={})]

        result.append(
            NamedLightAnimation(
                name=name,
                source_path=source_path,
                asset=LightSequenceAsset(
                    width=base_layout.width,
                    height=base_layout.height,
                    leds=base_layout.leds,
                    frames=tuple(frames),
                    background_path=base_layout.background_path,
                    source_path=source_path,
                ),
            )
        )

    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        # Let the existing loader handle regular JSON layouts/sequences.
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping at the top level")
    return data


def _load_base_layout_asset(data: dict[str, Any], source_path: Path) -> LightSequenceAsset:
    layout = data.get("layout")

    if isinstance(layout, str):
        return load_light_sequence((source_path.parent / layout).resolve())

    if isinstance(layout, dict) and "path" in layout and "leds" not in layout:
        return load_light_sequence((source_path.parent / str(layout["path"])).resolve())

    if "layout_file" in data:
        return load_light_sequence((source_path.parent / str(data["layout_file"])).resolve())

    # Reuse the existing loader by temporarily removing the multi-animation block
    # and presenting the embedded layout as a normal sequence with one blank frame.
    payload = dict(data)
    payload.pop("animations", None)
    payload.setdefault("frames", [{"duration_ms": 100, "leds": {}}])

    temp_path = source_path.with_name(f".{source_path.stem}.preview_layout.tmp.yaml")
    try:
        temp_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return load_light_sequence(temp_path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def _animation_items(raw: Any) -> list[tuple[str, Any]]:
    if isinstance(raw, dict):
        return [(str(name), value) for name, value in raw.items()]

    if isinstance(raw, list):
        items: list[tuple[str, Any]] = []
        for index, value in enumerate(raw):
            if not isinstance(value, dict):
                raise ValueError("Animation list entries must be mappings")
            name = str(value.get("id", value.get("name", f"animation_{index}")))
            items.append((name, value))
        return items

    raise ValueError("'animations' must be a mapping or a list")


def _parse_frames(raw_frames: Any, default_duration_ms: int) -> list[LightFrame]:
    if raw_frames is None:
        return []
    if not isinstance(raw_frames, list):
        raise ValueError("Animation 'frames' must be a list")
    return [_parse_frame(frame, default_duration_ms) for frame in raw_frames]


def _parse_frame(raw_frame: Any, default_duration_ms: int) -> LightFrame:
    if not isinstance(raw_frame, dict):
        raise ValueError("Frame entries must be mappings")

    duration_ms = int(raw_frame.get("duration_ms", default_duration_ms))
    raw_leds = raw_frame.get("leds", {})

    if isinstance(raw_leds, list):
        leds: dict[str, tuple[str, float]] = {}
        for raw_led in raw_leds:
            if not isinstance(raw_led, dict):
                raise ValueError("Frame LED list entries must be mappings")
            led_id = str(raw_led["id"])
            leds[led_id] = _parse_led_value(raw_led)
        return LightFrame(duration_ms=duration_ms, leds=leds)

    if isinstance(raw_leds, dict):
        return LightFrame(
            duration_ms=duration_ms,
            leds={str(led_id): _parse_led_value(value) for led_id, value in raw_leds.items()},
        )

    raise ValueError("Frame 'leds' must be a mapping or list")


def _parse_led_value(value: Any) -> tuple[str, float]:
    if isinstance(value, str):
        return value, 1.0

    if isinstance(value, dict):
        if value.get("off") is True:
            return "#202020", 0.0
        color = str(value.get("color", "#ffffff"))
        intensity = max(0.0, min(1.0, float(value.get("intensity", 1.0))))
        return color, intensity

    raise ValueError("LED values must be a color string or mapping")
