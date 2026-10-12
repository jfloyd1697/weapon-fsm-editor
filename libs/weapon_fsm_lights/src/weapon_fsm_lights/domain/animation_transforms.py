from __future__ import annotations

from copy import deepcopy

from weapon_fsm_lights.domain.animation_project import LightAnimationDef


def reverse_animation(animation: LightAnimationDef) -> LightAnimationDef:
    """
    Reverse timing.

    Each layer keeps the same duration, but its start time is mirrored around
    the animation duration.
    """
    copied = deepcopy(animation)

    for layer in copied.layers:
        layer_start = int(layer.start_ms)
        layer_duration = int(layer.duration_ms)
        layer_end = layer_start + layer_duration

        layer.start_ms = max(0, copied.duration_ms - layer_end)

    copied.layers = sorted(
        copied.layers,
        key=lambda item: (item.start_ms, item.name),
    )

    return copied


def invert_animation(animation: LightAnimationDef) -> LightAnimationDef:
    """
    Invert light/dark behavior.

    This toggles layer.invert, which makes the layer cut light out of layers
    below it instead of adding light.
    """
    copied = deepcopy(animation)

    for layer in copied.layers:
        layer.invert = not getattr(layer, "invert", False)

    return copied


def reverse_and_invert_animation(animation: LightAnimationDef) -> LightAnimationDef:
    return invert_animation(reverse_animation(animation))