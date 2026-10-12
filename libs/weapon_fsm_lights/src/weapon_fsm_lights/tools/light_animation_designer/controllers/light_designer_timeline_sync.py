from weapon_fsm_lights.domain.animation_project import LightAnimationDef
from ..widgets.timeline_widget import TimelineLayer, TimelineWidget


class LightDesignerTimelineSync:
    def __init__(self, timeline: TimelineWidget) -> None:
        self._timeline = timeline

    def clear(self) -> None:
        self._timeline.set_timeline(
            duration_ms=1000,
            layers=[],
            selected_row=None,
        )

    def refresh(
            self,
            *,
            animation: LightAnimationDef | None,
            selected_layer_index: int | None,
            enabled_layers: list[bool],
    ) -> None:
        if animation is None:
            self.clear()
            return

        self._timeline.set_timeline(
            duration_ms=animation.duration_ms,
            selected_row=selected_layer_index,
            layers=[
                TimelineLayer(
                    name=layer.name,
                    color=layer.color,
                    start_ms=layer.start_ms,
                    duration_ms=layer.duration_ms,
                    enabled=enabled_layers[index]
                    if index < len(enabled_layers)
                    else True,
                )
                for index, layer in enumerate(animation.layers)
            ],
        )

    def set_selected_layer(self, selected_layer_index: int | None) -> None:
        self._timeline.set_selected_row(selected_layer_index)
