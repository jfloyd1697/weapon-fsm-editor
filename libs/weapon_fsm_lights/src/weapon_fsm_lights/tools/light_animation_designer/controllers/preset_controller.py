from __future__ import annotations

import logging

from PyQt6.QtWidgets import QDialog

from weapon_fsm_lights.domain.animation_project import LightAnimationProject
from weapon_fsm_lights.domain.animation_transforms import (
    invert_animation,
    reverse_animation,
)

from ..widgets.preset_dialog import PresetDialog


LOGGER = logging.getLogger(__name__)


class PresetController:
    def __init__(self, window) -> None:
        self.window = window

    def connect(self) -> None:
        LOGGER.debug("PresetController.connect")
        self.window.ui.add_preset_button.clicked.connect(self.add_preset)

    def add_preset(self) -> None:
        window = self.window

        LOGGER.debug(
            "PresetController.add_preset start project=%r layout_asset=%r",
            window.project,
            window.layout_asset,
        )

        dialog = PresetDialog(
            layout_asset=window.layout_asset,
            parent=window,
        )

        LOGGER.debug("PresetController executing PresetDialog")
        result = dialog.exec()
        LOGGER.debug("PresetController PresetDialog closed result=%r", result)

        if result != QDialog.DialogCode.Accepted:
            LOGGER.debug("PresetController preset dialog canceled")
            return

        preset = dialog.selected_preset()
        LOGGER.debug("PresetController selected preset=%r", preset)

        if preset is None:
            LOGGER.debug("PresetController accepted with no preset")
            return

        before = window.undo_history.snapshot()

        if window.project is None:
            LOGGER.debug("PresetController creating new project for preset")
            window.project = LightAnimationProject(
                layout={"path": "layouts/cpx_ring.json"},
                animations={},
            )

        name = window.animation_controller.unique_name(preset.animation.name)
        animation = preset.create_animation(name=name)

        if dialog.reverse_animation_enabled():
            animation = reverse_animation(animation)
            animation.name = name

        if dialog.invert_animation_enabled():
            animation = invert_animation(animation)
            animation.name = name

        LOGGER.debug(
            "PresetController inserting preset animation name=%s layers=%s reverse=%s invert=%s",
            animation.name,
            len(animation.layers),
            dialog.reverse_animation_enabled(),
            dialog.invert_animation_enabled(),
        )

        window.project.animations[animation.name] = animation
        window.layer_enabled_by_animation[animation.name] = [
            True
        ] * len(animation.layers)

        window.animation_controller.reload_list()
        window.animation_controller.select_name(animation.name)
        window.timeline_controller.refresh()
        window.preview_controller.recompile(autoplay=False)
        window.record_undo("Add Animation Preset", before)

        LOGGER.debug("PresetController.add_preset complete")