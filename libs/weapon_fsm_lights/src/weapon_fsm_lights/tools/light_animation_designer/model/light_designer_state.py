from dataclasses import dataclass

from weapon_fsm_lights.domain.animation_project import LightAnimationProject


@dataclass(frozen=True)
class LightDesignerState:
    project: LightAnimationProject | None
    selected_animation: str | None
    selected_layer_index: int | None
    layer_enabled_by_animation: dict[str, list[bool]]
