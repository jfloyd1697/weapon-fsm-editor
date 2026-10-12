# weapon_fsm_lights/domain/compiler.py

from dataclasses import dataclass
import math
import random

from weapon_fsm_lights.infrastructure.loader import LedNode, LightFrame, LightSequenceAsset
from weapon_fsm_lights.domain.animation_project import LightAnimationDef
from weapon_fsm_lights.domain.animation_layers import (
    BlinkLayerDef,
    ChaseLayerDef,
    LightLayerDef,
    RadialPulseLayerDef,
    SolidLayerDef,
    SparkleLayerDef,
    WipeLayerDef,
)


@dataclass(frozen=True)
class LedSample:
    color: str
    intensity: float


def compile_animation(
    *,
    layout: LightSequenceAsset,
    animation: LightAnimationDef,
) -> LightSequenceAsset:
    frame_duration = max(1, int(animation.frame_duration_ms))
    duration = max(frame_duration, int(animation.duration_ms))
    frame_count = max(1, math.ceil(duration / frame_duration))

    frames: list[LightFrame] = []

    for frame_index in range(frame_count):
        time_ms = frame_index * frame_duration
        led_states: dict[str, tuple[str, float]] = {}

        for led in layout.leds:
            sample = sample_animation_at_led(
                animation=animation,
                led=led,
                time_ms=time_ms,
            )

            if sample.intensity > 0.0:
                led_states[led.id] = (
                    sample.color,
                    max(0.0, min(1.0, sample.intensity)),
                )

        frames.append(
            LightFrame(
                duration_ms=frame_duration,
                leds=led_states,
            )
        )

    return LightSequenceAsset(
        width=layout.width,
        height=layout.height,
        leds=layout.leds,
        frames=tuple(frames),
        background_path=layout.background_path,
        source_path=layout.source_path,
    )


def sample_animation_at_led(
    *,
    animation: LightAnimationDef,
    led: LedNode,
    time_ms: int,
) -> LedSample:
    result = LedSample(color="#202020", intensity=0.0)

    for layer in animation.layers:
        sample = sample_layer(
            layer=layer,
            led=led,
            time_ms=time_ms,
        )

        if sample.intensity >= result.intensity:
            result = sample

    return result


def sample_layer(
    *,
    layer: LightLayerDef,
    led: LedNode,
    time_ms: int,
) -> LedSample:
    if time_ms < layer.start_ms:
        return LedSample(layer.color, 0.0)

    local_ms = time_ms - layer.start_ms

    if local_ms > layer.duration_ms:
        return LedSample(layer.color, 0.0)

    progress = local_ms / max(1, layer.duration_ms)

    if isinstance(layer, SolidLayerDef):
        return _sample_solid(layer)

    if isinstance(layer, RadialPulseLayerDef):
        return _sample_radial_pulse(layer, led, progress)

    if isinstance(layer, WipeLayerDef):
        return _sample_wipe(layer, led, progress)

    if isinstance(layer, BlinkLayerDef):
        return _sample_blink(layer, progress)

    if isinstance(layer, ChaseLayerDef):
        return _sample_chase(layer, led, progress)

    if isinstance(layer, SparkleLayerDef):
        return _sample_sparkle(layer, led, time_ms)

    return LedSample(layer.color, 0.0)


def _sample_solid(layer: SolidLayerDef) -> LedSample:
    return LedSample(layer.color, layer.intensity)


def _sample_radial_pulse(
    layer: RadialPulseLayerDef,
    led: LedNode,
    progress: float,
) -> LedSample:
    cx, cy = layer.center
    dx = led.x - cx
    dy = led.y - cy
    distance = math.sqrt(dx * dx + dy * dy)

    active_radius = layer.radius_from + (
        layer.radius_to - layer.radius_from
    ) * progress

    half_width = max(0.0001, layer.width / 2.0)
    falloff = 1.0 - abs(distance - active_radius) / half_width
    intensity = max(0.0, min(1.0, falloff)) * layer.intensity

    return LedSample(layer.color, intensity)


def _sample_wipe(
    layer: WipeLayerDef,
    led: LedNode,
    progress: float,
) -> LedSample:
    dx, dy = layer.direction
    length = math.sqrt(dx * dx + dy * dy) or 1.0
    nx = dx / length
    ny = dy / length

    position = led.x * nx + led.y * ny
    active_position = progress * layer.speed

    half_width = max(0.0001, layer.width / 2.0)
    falloff = 1.0 - abs(position - active_position) / half_width
    intensity = max(0.0, min(1.0, falloff)) * layer.intensity

    return LedSample(layer.color, intensity)


def _sample_blink(
    layer: BlinkLayerDef,
    progress: float,
) -> LedSample:
    cycles = max(0.0, layer.speed)
    phase = (progress * cycles) % 1.0 if cycles > 0 else progress
    intensity = layer.intensity if phase < 0.5 else 0.0
    return LedSample(layer.color, intensity)


def _sample_chase(
    layer: ChaseLayerDef,
    led: LedNode,
    progress: float,
) -> LedSample:
    if led.index is None:
        return LedSample(layer.color, 0.0)

    position = (progress * layer.speed) % 1.0
    led_position = (led.index % 1000) / 1000.0

    half_width = max(0.0001, layer.width / 2.0)
    distance = abs(led_position - position)
    distance = min(distance, 1.0 - distance)

    falloff = 1.0 - distance / half_width
    intensity = max(0.0, min(1.0, falloff)) * layer.intensity

    return LedSample(layer.color, intensity)


def _sample_sparkle(
    layer: SparkleLayerDef,
    led: LedNode,
    time_ms: int,
) -> LedSample:
    led_index = led.index if led.index is not None else int(led.id)
    bucket = time_ms // max(1, int(100 / max(0.01, layer.speed)))

    rng = random.Random(layer.seed + led_index * 131 + bucket * 17)
    enabled = rng.random() < layer.density

    return LedSample(
        layer.color,
        layer.intensity if enabled else 0.0,
    )