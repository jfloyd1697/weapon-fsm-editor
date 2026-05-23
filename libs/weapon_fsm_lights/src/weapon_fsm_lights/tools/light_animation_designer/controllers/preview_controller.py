from PyQt6.QtGui import QColor, QIcon, QPixmap

from .timeline_controller import Window
from weapon_fsm_lights.domain.compiler import compile_animation



class PreviewController:
    def __init__(self, window: Window) -> None:
        self.window = window

    def connect(self) -> None:
        ui = self.window.ui
        ui.recompile_button.clicked.connect(self.recompile)
        ui.show_canvas_button.toggled.connect(self.show_canvas)

    def show_canvas(self, show_canvas: bool) -> None:
        canvas = self.window.ui.canvas

        if hasattr(canvas, "set_show_canvas"):
            canvas.set_show_canvas(show_canvas)
        elif hasattr(canvas, "show_canvas"):
            canvas.show_canvas(show_canvas)

        self.window.ui.show_canvas_button.setText(
            "Hide Canvas" if show_canvas else "Show Canvas"
        )

    def recompile(self, autoplay: bool | None = None) -> None:
        window = self.window

        if window.layout_asset is None:
            return

        animation = window.context.current_animation()

        if animation is None:
            return

        try:
            was_playing = window.ui.player.is_playing if autoplay is None else autoplay
            preview_animation = window.context.preview_animation(animation)

            if hasattr(window.ui.canvas, "set_canvas_animation"):
                window.ui.canvas.set_canvas_animation(preview_animation)

            compiled = compile_animation(
                layout=window.layout_asset,
                animation=preview_animation,
            )

            window.ui.canvas.play_sequence(
                compiled,
                sequence_name=animation.name,
                mode=animation.mode.value,
            )
            window.ui.player.set_asset(
                compiled,
                sequence_name=animation.name,
                mode=animation.mode.value,
                autoplay=was_playing,
            )

            enabled_count = len(preview_animation.layers)
            total_count = len(animation.layers)

            window.ui.status_label.setText(
                f"Preview: {animation.name} "
                f"({len(compiled.frames)} frames, "
                f"{enabled_count}/{total_count} layers enabled)"
            )

        except Exception as exc:  # noqa: BLE001
            window.ui.status_label.setText(f"Compile failed: {exc}")

    def icon_for_animation(self, animation) -> QIcon:
        return self.icon_for_color(self.animation_icon_color(animation))

    def animation_icon_color(self, animation) -> str:
        best_color = "#202020"
        best_intensity = -1.0

        for layer in animation.layers:
            if layer.intensity >= best_intensity:
                best_color = layer.color
                best_intensity = layer.intensity

        return best_color

    def icon_for_color(self, color_text: str) -> QIcon:
        color = QColor(color_text if color_text else "#202020")

        if not color.isValid():
            color = QColor("#202020")

        pixmap = QPixmap(16, 16)
        pixmap.fill(color)

        return QIcon(pixmap)

    def refresh_current_animation_icon(self) -> None:
        window = self.window

        if window.selected_animation is None:
            return

        animation = window.context.current_animation()
        if animation is None:
            return

        for row in range(window.ui.animation_list.count()):
            item = window.ui.animation_list.item(row)

            if item is not None and item.text() == window.selected_animation:
                item.setIcon(self.icon_for_animation(animation))
                break
