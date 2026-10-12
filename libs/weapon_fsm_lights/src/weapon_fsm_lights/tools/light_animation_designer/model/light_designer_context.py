from copy import deepcopy

from weapon_fsm_lights.domain.animation_layers import LightLayerDef
from weapon_fsm_lights.domain.animation_project import LightAnimationDef

from weapon_fsm_lights.tools.light_animation_designer.model.light_designer_state import LightDesignerState


class LightDesignerContext:
    def __init__(self, window) -> None:
        self.window = window

    def capture_state(self) -> LightDesignerState:
        window = self.window
        return LightDesignerState(
            project=deepcopy(window.project),
            selected_animation=window.selected_animation,
            selected_layer_index=window.selected_layer_index,
            layer_enabled_by_animation=deepcopy(window.layer_enabled_by_animation),
        )

    def restore_state(self, state: LightDesignerState) -> None:
        window = self.window
        window.project = deepcopy(state.project)
        window.selected_animation = state.selected_animation
        window.selected_layer_index = state.selected_layer_index
        window.layer_enabled_by_animation = deepcopy(state.layer_enabled_by_animation)

    def current_animation(self) -> LightAnimationDef | None:
        window = self.window

        if window.project is None or window.selected_animation is None:
            return None

        return window.project.animations.get(window.selected_animation)

    def current_layer(self) -> LightLayerDef | None:
        window = self.window
        animation = self.current_animation()

        if animation is None or window.selected_layer_index is None:
            return None

        if not (0 <= window.selected_layer_index < len(animation.layers)):
            return None

        return animation.layers[window.selected_layer_index]

    def layer_enabled_for_animation(self, animation: LightAnimationDef) -> list[bool]:
        window = self.window

        if window.selected_animation is None:
            return [True] * len(animation.layers)

        existing = list(
            window.layer_enabled_by_animation.get(window.selected_animation, [])
        )

        if len(existing) < len(animation.layers):
            existing.extend([True] * (len(animation.layers) - len(existing)))

        if len(existing) > len(animation.layers):
            existing = existing[: len(animation.layers)]

        window.layer_enabled_by_animation[window.selected_animation] = existing
        return existing

    def enabled_layer_indexes(self, animation: LightAnimationDef) -> list[int]:
        enabled = self.layer_enabled_for_animation(animation)
        return [index for index, is_enabled in enumerate(enabled) if is_enabled]

    def preview_animation(self, animation: LightAnimationDef) -> LightAnimationDef:
        enabled_indexes = set(self.enabled_layer_indexes(animation))

        return LightAnimationDef(
            name=animation.name,
            frame_duration_ms=animation.frame_duration_ms,
            duration_ms=animation.duration_ms,
            mode=animation.mode,
            layers=[
                layer
                for index, layer in enumerate(animation.layers)
                if index in enabled_indexes
            ],
        )
