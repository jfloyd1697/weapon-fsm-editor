from pathlib import Path

import yaml

from weapon_fsm_lights.domain.animation_project import LightAnimationProject
from weapon_fsm_lights.infrastructure.loader import LightSequenceAsset, load_light_sequence


def load_authored_project(path: str | Path) -> LightAnimationProject:
    project_path = Path(path).expanduser().resolve()
    data = yaml.safe_load(project_path.read_text(encoding="utf-8")) or {}

    if not isinstance(data, dict):
        raise ValueError("Light animation project must contain a mapping")

    try:
        return LightAnimationProject.from_dict(data)
    except Exception as exc:
        raise ValueError(f"Failed to load light animation project {project_path}: {exc}") from exc


def save_authored_project(path: str | Path, project: LightAnimationProject) -> None:
    project_path = Path(path).expanduser().resolve()
    project_path.write_text(
        yaml.safe_dump(
            project.to_dict(),
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def load_project_layout(
    project_path: str | Path,
    project: LightAnimationProject,
) -> LightSequenceAsset:
    source_path = Path(project_path).expanduser().resolve()
    layout = project.layout

    if isinstance(layout, str):
        layout_path = source_path.parent / layout
    elif isinstance(layout, dict) and "path" in layout:
        layout_path = source_path.parent / str(layout["path"])
    else:
        raise ValueError("Project must define layout.path")

    return load_light_sequence(layout_path)