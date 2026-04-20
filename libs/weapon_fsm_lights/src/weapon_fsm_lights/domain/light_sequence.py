from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LedNode:
    id: str
    x: float
    y: float
    radius: float = 10.0
    label: str | None = None
    index: int | None = None


@dataclass(frozen=True)
class LightFrame:
    duration_ms: int
    leds: dict[str, tuple[str, float]]


@dataclass(frozen=True)
class LightSequenceAsset:
    width: float
    height: float
    leds: tuple[LedNode, ...]
    frames: tuple[LightFrame, ...]
    background_path: Path | None = None
    source_path: Path | None = None

    @property
    def has_frames(self) -> bool:
        return bool(self.frames)


class LightSequenceError(ValueError):
    pass


def load_light_sequence(path: str | Path) -> LightSequenceAsset:
    source_path = Path(path).expanduser().resolve()
    data = _load_mapping_file(source_path)
    if source_path.suffix.lower() == ".json" and "coordinate_space" in data and "leds" in data:
        return _load_layout_json_asset(data, source_path)

    layout_block = _resolve_layout_block(data, source_path)
    width = float(layout_block.get("width", data.get("width", 640)))
    height = float(layout_block.get("height", data.get("height", 240)))
    background_path = _resolve_background_path(layout_block, data, source_path)

    led_entries = layout_block.get("leds", data.get("leds", []))
    if not isinstance(led_entries, list) or not led_entries:
        raise LightSequenceError(
            f"Light sequence at {source_path} must define at least one LED in 'layout.leds'"
        )

    leds = tuple(_parse_led_node(entry) for entry in led_entries)
    default_duration = int(data.get("frame_duration_ms", 100))
    frames_block = data.get("frames", [])
    frames: tuple[LightFrame, ...]
    if not frames_block:
        frames = (LightFrame(duration_ms=default_duration, leds={}),)
    else:
        if not isinstance(frames_block, list):
            raise LightSequenceError(
                f"Light sequence at {source_path} must define 'frames' as a list"
            )
        frames = tuple(_parse_frame(frame, default_duration) for frame in frames_block)

    _validate_frame_led_ids(leds, frames, source_path)
    return LightSequenceAsset(
        width=width,
        height=height,
        leds=leds,
        frames=frames,
        background_path=background_path,
        source_path=source_path,
    )


def validate_light_sequence(path: str | Path) -> list[str]:
    try:
        load_light_sequence(path)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def _load_mapping_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8")) or {}
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise LightSequenceError(f"File at {path} must contain a mapping/object at the top level")
    return data


def _load_layout_json_asset(data: dict[str, Any], source_path: Path) -> LightSequenceAsset:
    if str(data.get("coordinate_space", "")) != "normalized_2d":
        raise LightSequenceError(
            f"Layout JSON at {source_path} must use coordinate_space='normalized_2d'"
        )
    raw_leds = data.get("leds", [])
    if not isinstance(raw_leds, list) or not raw_leds:
        raise LightSequenceError(f"Layout JSON at {source_path} must contain a non-empty 'leds' list")
    leds: list[LedNode] = []
    for item in raw_leds:
        if not isinstance(item, dict):
            raise LightSequenceError("Each layout LED entry must be an object")
        index = int(item.get("index", len(leds)))
        led_id = str(item.get("id", index))
        u = float(item["u"])
        v = float(item["v"])
        radius = float(item.get("led_radius", item.get("radius", 0.02)))
        leds.append(
            LedNode(
                id=led_id,
                x=u,
                y=v,
                radius=radius,
                label=str(item.get("label")) if item.get("label") is not None else None,
                index=index,
            )
        )
    return LightSequenceAsset(
        width=1.0,
        height=1.0,
        leds=tuple(leds),
        frames=(LightFrame(duration_ms=100, leds={}),),
        background_path=None,
        source_path=source_path,
    )




def _normalize_layout_mapping(data: dict[str, Any]) -> dict[str, Any]:
    if str(data.get("coordinate_space", "")) != "normalized_2d" or "leds" not in data:
        return data
    leds = []
    for item in data.get("leds", []):
        if not isinstance(item, dict):
            raise LightSequenceError("Each layout LED entry must be an object")
        index = int(item.get("index", len(leds)))
        leds.append({
            "id": str(item.get("id", index)),
            "index": index,
            "x": float(item["u"]),
            "y": float(item["v"]),
            "radius": float(item.get("led_radius", item.get("radius", 0.02))),
            **({"label": str(item["label"])} if item.get("label") is not None else {}),
        })
    return {"width": 1.0, "height": 1.0, "leds": leds}

def _resolve_layout_block(data: dict[str, Any], source_path: Path) -> dict[str, Any]:
    if "layout_file" in data:
        layout_path = (source_path.parent / str(data["layout_file"])).resolve()
        return _normalize_layout_mapping(_load_mapping_file(layout_path))

    layout_block = data.get("layout", {})
    if isinstance(layout_block, dict):
        if "path" in layout_block and "leds" not in layout_block:
            layout_path = (source_path.parent / str(layout_block["path"])).resolve()
            return _normalize_layout_mapping(_load_mapping_file(layout_path))
        return layout_block

    raise LightSequenceError("'layout' must be a mapping when provided")


def _resolve_background_path(
    layout_block: dict[str, Any],
    data: dict[str, Any],
    source_path: Path,
) -> Path | None:
    background = layout_block.get("background") or data.get("background")
    if not background:
        return None
    return (source_path.parent / str(background)).resolve()


def _parse_led_node(entry: Any) -> LedNode:
    if not isinstance(entry, dict):
        raise LightSequenceError("Each LED entry must be a mapping")

    led_id = str(entry["id"])
    x = float(entry["x"])
    y = float(entry["y"])
    radius = float(entry.get("radius", 10.0))
    label = str(entry["label"]) if entry.get("label") is not None else None
    index = int(entry["index"]) if entry.get("index") is not None else None
    return LedNode(id=led_id, x=x, y=y, radius=radius, label=label, index=index)


def _parse_frame(entry: Any, default_duration: int) -> LightFrame:
    if not isinstance(entry, dict):
        raise LightSequenceError("Each frame entry must be a mapping")

    duration_ms = int(entry.get("duration_ms", default_duration))
    led_states = entry.get("leds", {})
    if isinstance(led_states, list):
        led_map = {}
        for item in led_states:
            if not isinstance(item, dict):
                raise LightSequenceError("Frame LED list entries must be mappings")
            led_id = str(item["id"])
            led_map[led_id] = _parse_led_value(item)
        return LightFrame(duration_ms=duration_ms, leds=led_map)

    if not isinstance(led_states, dict):
        raise LightSequenceError("Frame 'leds' must be a mapping or list")

    parsed = {str(led_id): _parse_led_value(value) for led_id, value in led_states.items()}
    return LightFrame(duration_ms=duration_ms, leds=parsed)


def _parse_led_value(value: Any) -> tuple[str, float]:
    if isinstance(value, str):
        return value, 1.0

    if isinstance(value, dict):
        if value.get("off") is True:
            return "#202020", 0.0
        color = str(value.get("color", "#ffffff"))
        intensity = float(value.get("intensity", 1.0))
        intensity = max(0.0, min(1.0, intensity))
        return color, intensity

    raise LightSequenceError("LED values must be a color string or mapping")


def _validate_frame_led_ids(
    leds: tuple[LedNode, ...],
    frames: tuple[LightFrame, ...],
    source_path: Path,
) -> None:
    allowed = {led.id for led in leds}
    for frame_index, frame in enumerate(frames):
        for led_id in frame.leds:
            if led_id not in allowed:
                raise LightSequenceError(
                    f"Light sequence at {source_path} references unknown LED '{led_id}' in frame {frame_index}"
                )
