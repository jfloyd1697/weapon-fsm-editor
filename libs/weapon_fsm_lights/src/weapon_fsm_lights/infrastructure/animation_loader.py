from pathlib import Path
from typing import Any

import yaml

from weapon_fsm_lights.domain.animation_project import LightAnimationDef
from weapon_fsm_lights.domain.compiler import compile_animation
from weapon_fsm_lights.infrastructure.loader import LightSequenceAsset, load_light_sequence


def load_canvas_animation_sequence(path: str | Path) -> LightSequenceAsset:
    source_path = Path(path).expanduser().resolve()
    data = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}

    if not isinstance(data, dict):
        raise ValueError("Canvas animation file must contain a mapping")

    layout_path = _resolve_layout_path(data, source_path)
    layout = load_light_sequence(layout_path)
    animation_raw = dict(data.get("animation", data))
    animation = LightAnimationDef.from_dict(animation_raw)

    return compile_animation(layout=layout, animation=animation)


def _resolve_layout_path(data: dict[str, Any], source_path: Path) -> Path:
    layout = data.get("layout")

    if isinstance(layout, str):
        return (source_path.parent / layout).resolve()

    if isinstance(layout, dict) and "path" in layout:
        return (source_path.parent / str(layout["path"])).resolve()

    if "layout_file" in data:
        return (source_path.parent / str(data["layout_file"])).resolve()

    raise ValueError("Canvas animation must define layout.path or layout_file")
