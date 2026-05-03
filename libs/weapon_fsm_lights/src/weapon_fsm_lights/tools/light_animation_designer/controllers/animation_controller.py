from copy import deepcopy

from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QListWidgetItem

from light_animation_designer.controllers.timeline_controller import Window
from weapon_fsm_lights.domain.animation_layers import SolidLayerDef
from weapon_fsm_lights.domain.animation_project import (
    LightAnimationDef,
    LightAnimationMode,
    LightAnimationProject,
)


class AnimationController:
    def __init__(self, window: Window) -> None:
        self.window = window

    def connect(self) -> None:
        ui = self.window.ui
        ui.animation_list.currentItemChanged.connect(self.on_selected)
        ui.add_animation_button.clicked.connect(self.add)
        ui.duplicate_animation_button.clicked.connect(self.duplicate)
        ui.delete_animation_button.clicked.connect(self.delete)

        ui.animation_name_edit.lineEdit().editingFinished.connect(self.apply_controls)
        ui.animation_mode.currentTextChanged.connect(self.apply_controls)
        ui.animation_duration_ms.valueChanged.connect(self.apply_controls)
        ui.animation_frame_ms.valueChanged.connect(self.apply_controls)

    def reload_list(self) -> None:
        window = self.window
        ui = window.ui

        with QSignalBlocker(ui.animation_list):
            ui.animation_list.clear()
            ui.layer_list.clear()

            if window.project is None:
                return

            for name, animation in window.project.animations.items():
                item = QListWidgetItem(name)
                item.setIcon(window.preview_controller.icon_for_animation(animation))
                ui.animation_list.addItem(item)

        if ui.animation_list.count() > 0:
            ui.animation_list.setCurrentRow(0)
            current = ui.animation_list.currentItem()
            self.on_selected(current)
        else:
            window.selected_animation = None
            window.selected_layer_index = None
            ui.layer_properties.clear_layer()
            window.timeline_controller.refresh()

    def on_selected(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None = None,
    ) -> None:
        window = self.window

        if window.project is None or current is None:
            return

        window.selected_animation = current.text()
        window.selected_layer_index = None

        self.load_controls()
        window.layer_controller.reload_list()
        window.preview_controller.recompile(autoplay=False)
        window.timeline_controller.refresh()

    def load_controls(self) -> None:
        window = self.window
        ui = window.ui
        animation = window.context.current_animation()

        if animation is None:
            return

        window.updating_controls = True

        try:
            with QSignalBlocker(ui.animation_name_edit):
                ui.animation_name_edit.clear()
                ui.animation_name_edit.addItem(animation.name)
                ui.animation_name_edit.setCurrentText(animation.name)

            with QSignalBlocker(ui.animation_mode):
                ui.animation_mode.setCurrentText(animation.mode.value)

            with QSignalBlocker(ui.animation_duration_ms):
                ui.animation_duration_ms.setValue(animation.duration_ms)

            with QSignalBlocker(ui.animation_frame_ms):
                ui.animation_frame_ms.setValue(animation.frame_duration_ms)

        finally:
            window.updating_controls = False

    def apply_controls(self) -> None:
        window = self.window
        ui = window.ui

        if window.updating_controls or window.undo_history.is_restoring:
            return

        animation = window.context.current_animation()

        if animation is None:
            return

        before = window.undo_history.snapshot()

        old_name = window.selected_animation
        new_name = ui.animation_name_edit.currentText().strip() or animation.name

        animation.name = new_name
        animation.mode = LightAnimationMode(ui.animation_mode.currentText())
        animation.duration_ms = ui.animation_duration_ms.value()
        animation.frame_duration_ms = ui.animation_frame_ms.value()

        if (
            window.project is not None
            and old_name is not None
            and animation.name != old_name
        ):
            old_enabled = window.layer_enabled_by_animation.pop(old_name, None)
            window.project.animations.pop(old_name)
            window.project.animations[animation.name] = animation
            window.selected_animation = animation.name

            if old_enabled is not None:
                window.layer_enabled_by_animation[animation.name] = old_enabled

            self.reload_list()
            self.select_name(animation.name)

        window.preview_controller.refresh_current_animation_icon()
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=ui.player.is_playing)
        window.record_undo("Edit Animation", before)

    def add(self) -> None:
        window = self.window
        before = window.undo_history.snapshot()

        if window.project is None:
            window.project = LightAnimationProject(
                layout={"path": "layouts/cpx_ring.json"},
                animations={},
            )

        name = self.unique_name("new_animation")

        window.project.animations[name] = LightAnimationDef(
            name=name,
            layers=[
                SolidLayerDef(
                    name="solid",
                    intensity=0.4,
                )
            ],
        )

        window.layer_enabled_by_animation[name] = [True]
        self.reload_list()
        self.select_name(name)
        window.timeline_controller.refresh()
        window.record_undo("Add Animation", before)

    def duplicate(self) -> None:
        window = self.window
        animation = window.context.current_animation()

        if window.project is None or animation is None:
            return

        before = window.undo_history.snapshot()

        name = self.unique_name(f"{animation.name}_copy")
        copied = deepcopy(animation)
        copied.name = name

        window.project.animations[name] = copied
        window.layer_enabled_by_animation[name] = list(
            window.context.layer_enabled_for_animation(animation)
        )

        self.reload_list()
        self.select_name(name)
        window.timeline_controller.refresh()
        window.record_undo("Duplicate Animation", before)

    def delete(self) -> None:
        window = self.window

        if window.project is None or window.selected_animation is None:
            return

        before = window.undo_history.snapshot()

        window.project.animations.pop(window.selected_animation, None)
        window.layer_enabled_by_animation.pop(window.selected_animation, None)
        window.selected_animation = None
        window.selected_layer_index = None

        self.reload_list()
        window.timeline_controller.refresh()
        window.record_undo("Delete Animation", before)

    def select_name(self, name: str) -> None:
        ui = self.window.ui

        for row in range(ui.animation_list.count()):
            item = ui.animation_list.item(row)

            if item is not None and item.text() == name:
                ui.animation_list.setCurrentRow(row)
                return

    def unique_name(self, base: str) -> str:
        existing = set(self.window.project.animations if self.window.project is not None else {})

        if base not in existing:
            return base

        index = 2
        while f"{base}_{index}" in existing:
            index += 1

        return f"{base}_{index}"
