from copy import deepcopy

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtWidgets import QListWidgetItem

from light_animation_designer.controllers.timeline_controller import Window
from weapon_fsm_lights.domain.animation_layers import LightLayerDef, SolidLayerDef


class LayerController:
    def __init__(self, window: Window) -> None:
        self.window = window

    def connect(self) -> None:
        ui = self.window.ui
        ui.layer_list.currentRowChanged.connect(self.on_selected)
        ui.layer_list.itemChanged.connect(self.on_item_changed)

        ui.add_layer_button.clicked.connect(self.add)
        ui.duplicate_layer_button.clicked.connect(self.duplicate)
        ui.delete_layer_button.clicked.connect(self.delete)
        ui.move_layer_up_button.clicked.connect(lambda: self.move(-1))
        ui.move_layer_down_button.clicked.connect(lambda: self.move(1))
        ui.enable_all_layers_button.clicked.connect(self.enable_all)
        ui.only_selected_layer_button.clicked.connect(self.only_selected)

        ui.layer_properties.layer_changed.connect(self.on_properties_changed)

    def reload_list(self) -> None:
        window = self.window
        ui = window.ui
        animation = window.context.current_animation()

        with QSignalBlocker(ui.layer_list):
            ui.layer_list.clear()

            if animation is None:
                ui.layer_properties.clear_layer()
                window.timeline_controller.refresh()
                return

            enabled = window.context.layer_enabled_for_animation(animation)

            for index, layer in enumerate(animation.layers):
                item = QListWidgetItem(f"{layer.name} ({layer.type})")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked
                    if enabled[index]
                    else Qt.CheckState.Unchecked
                )
                item.setIcon(window.preview_controller.icon_for_color(layer.color))
                ui.layer_list.addItem(item)

        if ui.layer_list.count() > 0:
            ui.layer_list.setCurrentRow(0)
        else:
            window.selected_layer_index = None
            ui.layer_properties.clear_layer()

        window.timeline_controller.refresh()

    def reload_list_preserve_selection(self) -> None:
        window = self.window
        row = window.selected_layer_index or 0
        window.updating_lists = True

        try:
            self.reload_list()

            if window.ui.layer_list.count() > 0:
                row = min(row, window.ui.layer_list.count() - 1)
                window.ui.layer_list.setCurrentRow(row)

        finally:
            window.updating_lists = False

        window.timeline_controller.refresh()

    def on_selected(self, row: int) -> None:
        self.window.selected_layer_index = row if row >= 0 else None
        self.load_controls()
        self.window.timeline_controller.set_selected_layer(
            self.window.selected_layer_index
        )

    def load_controls(self) -> None:
        self.window.ui.layer_properties.set_layer(
            self.window.ui.layer_list.currentRow(),
            self.window.context.current_layer(),
        )

    def on_item_changed(self, item: QListWidgetItem) -> None:
        window = self.window

        if (
            window.updating_controls
            or window.updating_lists
            or window.undo_history.is_restoring
        ):
            return

        animation = window.context.current_animation()

        if animation is None or window.selected_animation is None:
            return

        before = window.undo_history.snapshot()

        states = [
            list_item.checkState() == Qt.CheckState.Checked
            for index in range(window.ui.layer_list.count())
            if (list_item := window.ui.layer_list.item(index)) is not None
        ]

        window.layer_enabled_by_animation[window.selected_animation] = states
        window.preview_controller.recompile(autoplay=window.ui.player.is_playing)
        window.timeline_controller.refresh()
        window.record_undo("Toggle Layer Preview", before)

    def on_properties_changed(self, row, updated_layer: LightLayerDef) -> None:
        window = self.window

        if window.undo_history.is_restoring:
            return

        animation = window.context.current_animation()

        if animation is None or window.selected_layer_index is None:
            return

        if not (0 <= window.selected_layer_index < len(animation.layers)):
            return

        before = window.undo_history.snapshot()

        animation.layers[window.selected_layer_index] = updated_layer

        self.update_row(row, updated_layer)
        window.preview_controller.refresh_current_animation_icon()
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=window.ui.player.is_playing)
        window.record_undo("Edit Layer", before)

    def add(self) -> None:
        window = self.window
        animation = window.context.current_animation()

        if animation is None:
            return

        before = window.undo_history.snapshot()

        animation.layers.append(
            SolidLayerDef(
                name="New Layer",
                intensity=0.4,
            )
        )

        enabled = window.context.layer_enabled_for_animation(animation)
        enabled.append(True)

        self.reload_list()
        window.ui.layer_list.setCurrentRow(len(animation.layers) - 1)
        window.preview_controller.refresh_current_animation_icon()
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=window.ui.player.is_playing)
        window.record_undo("Add Layer", before)

    def duplicate(self) -> None:
        window = self.window
        animation = window.context.current_animation()
        layer = window.context.current_layer()

        if animation is None or layer is None:
            return

        before = window.undo_history.snapshot()

        copied = deepcopy(layer)
        copied.name = f"{layer.name} copy"
        animation.layers.append(copied)

        enabled = window.context.layer_enabled_for_animation(animation)
        enabled.append(True)

        self.reload_list()
        window.ui.layer_list.setCurrentRow(len(animation.layers) - 1)
        window.preview_controller.refresh_current_animation_icon()
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=window.ui.player.is_playing)
        window.record_undo("Duplicate Layer", before)

    def delete(self) -> None:
        window = self.window
        animation = window.context.current_animation()

        if animation is None or window.selected_layer_index is None:
            return

        if not (0 <= window.selected_layer_index < len(animation.layers)):
            return

        before = window.undo_history.snapshot()

        animation.layers.pop(window.selected_layer_index)

        enabled = window.context.layer_enabled_for_animation(animation)
        if window.selected_layer_index < len(enabled):
            enabled.pop(window.selected_layer_index)

        self.reload_list()
        window.preview_controller.refresh_current_animation_icon()
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=window.ui.player.is_playing)
        window.record_undo("Delete Layer", before)

    def move(self, direction: int) -> None:
        window = self.window
        animation = window.context.current_animation()

        if animation is None or window.selected_layer_index is None:
            return

        old = window.selected_layer_index
        new = old + direction

        if new < 0 or new >= len(animation.layers):
            return

        before = window.undo_history.snapshot()

        animation.layers[old], animation.layers[new] = (
            animation.layers[new],
            animation.layers[old],
        )

        enabled = window.context.layer_enabled_for_animation(animation)
        enabled[old], enabled[new] = enabled[new], enabled[old]

        self.reload_list()
        window.ui.layer_list.setCurrentRow(new)
        window.preview_controller.refresh_current_animation_icon()
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=window.ui.player.is_playing)
        window.record_undo("Move Layer", before)

    def enable_all(self) -> None:
        window = self.window
        animation = window.context.current_animation()

        if animation is None or window.selected_animation is None:
            return

        before = window.undo_history.snapshot()

        window.layer_enabled_by_animation[window.selected_animation] = [
            True
        ] * len(animation.layers)

        self.reload_list_preserve_selection()
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=window.ui.player.is_playing)
        window.record_undo("Enable All Layers", before)

    def only_selected(self) -> None:
        window = self.window
        animation = window.context.current_animation()

        if (
            animation is None
            or window.selected_animation is None
            or window.selected_layer_index is None
        ):
            return

        before = window.undo_history.snapshot()

        window.layer_enabled_by_animation[window.selected_animation] = [
            index == window.selected_layer_index
            for index in range(len(animation.layers))
        ]

        self.reload_list_preserve_selection()
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=window.ui.player.is_playing)
        window.record_undo("Only Selected Layer", before)

    def update_row(self, row, layer) -> None:
        item = self.window.ui.layer_list.item(row)

        if item is None:
            return

        item.setText(f"{layer.name} ({layer.type})")
        item.setIcon(self.window.preview_controller.icon_for_color(layer.color))
