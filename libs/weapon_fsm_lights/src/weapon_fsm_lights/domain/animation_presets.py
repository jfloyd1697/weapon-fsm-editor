from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from weapon_fsm_lights.domain.animation_layers import (
    BlinkLayerDef,
    ChaseLayerDef,
    LightLayerDef,
    RadialPulseLayerDef,
    SolidLayerDef,
    SparkleLayerDef,
    WipeLayerDef,
)
from weapon_fsm_lights.domain.animation_project import (
    LightAnimationDef,
    LightAnimationMode,
)


@dataclass(frozen=True)
class AnimationPreset:
    name: str
    category: str
    description: str
    animation: LightAnimationDef

    def create_animation(self, name: str | None = None) -> LightAnimationDef:
        copied = deepcopy(self.animation)

        if name is not None:
            copied.name = name

        return copied


def make_animation(
    *,
    name: str,
    duration_ms: int,
    layers: list[LightLayerDef],
    mode: LightAnimationMode = LightAnimationMode.LOOP,
    frame_duration_ms: int = 33,
) -> LightAnimationDef:
    return LightAnimationDef(
        name=name,
        duration_ms=duration_ms,
        frame_duration_ms=frame_duration_ms,
        mode=mode,
        layers=layers,
    )


def all_animation_presets() -> list[AnimationPreset]:
    return [
        *solid_presets(),
        *blink_presets(),
        *radial_pulse_presets(),
        *wipe_presets(),
        *chase_presets(),
        *sparkle_presets(),
        *combo_presets(),
    ]


def presets_by_category() -> dict[str, list[AnimationPreset]]:
    grouped: dict[str, list[AnimationPreset]] = {}

    for preset in all_animation_presets():
        grouped.setdefault(preset.category, []).append(preset)

    return grouped


def preset_names() -> list[str]:
    return [preset.name for preset in all_animation_presets()]


def find_preset(name: str) -> AnimationPreset | None:
    normalized = name.casefold()

    for preset in all_animation_presets():
        if preset.name.casefold() == normalized:
            return preset

    return None


def solid_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="solid_blue_idle",
            category="Solid",
            description="Soft blue idle glow.",
            animation=make_animation(
                name="solid_blue_idle",
                duration_ms=1000,
                layers=[
                    SolidLayerDef(
                        name="blue idle",
                        color="#1e88ff",
                        intensity=0.35,
                        start_ms=0,
                        duration_ms=1000,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="solid_red_alert",
            category="Solid",
            description="Steady red alert state.",
            animation=make_animation(
                name="solid_red_alert",
                duration_ms=1000,
                layers=[
                    SolidLayerDef(
                        name="red alert",
                        color="#ff2020",
                        intensity=0.9,
                        start_ms=0,
                        duration_ms=1000,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="solid_green_ready",
            category="Solid",
            description="Steady green ready state.",
            animation=make_animation(
                name="solid_green_ready",
                duration_ms=1000,
                layers=[
                    SolidLayerDef(
                        name="green ready",
                        color="#20ff70",
                        intensity=0.7,
                        start_ms=0,
                        duration_ms=1000,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="solid_warm_white",
            category="Solid",
            description="Warm white lamp-like glow.",
            animation=make_animation(
                name="solid_warm_white",
                duration_ms=1000,
                layers=[
                    SolidLayerDef(
                        name="warm white",
                        color="#ffd89a",
                        intensity=0.6,
                        start_ms=0,
                        duration_ms=1000,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="solid_dim_amber",
            category="Solid",
            description="Low amber standby glow.",
            animation=make_animation(
                name="solid_dim_amber",
                duration_ms=1000,
                layers=[
                    SolidLayerDef(
                        name="dim amber",
                        color="#ff9900",
                        intensity=0.25,
                        start_ms=0,
                        duration_ms=1000,
                    ),
                ],
            ),
        ),
    ]


def blink_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="blink_red_warning",
            category="Blink",
            description="Slow red warning blink.",
            animation=make_animation(
                name="blink_red_warning",
                duration_ms=1200,
                layers=[
                    BlinkLayerDef(
                        name="red warning blink",
                        color="#ff2020",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=1200,
                        speed=2.0,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="blink_fast_white_strobe",
            category="Blink",
            description="Fast white strobe.",
            animation=make_animation(
                name="blink_fast_white_strobe",
                duration_ms=600,
                layers=[
                    BlinkLayerDef(
                        name="white strobe",
                        color="#ffffff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=600,
                        speed=8.0,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="blink_blue_status",
            category="Blink",
            description="Medium blue status blink.",
            animation=make_animation(
                name="blink_blue_status",
                duration_ms=1500,
                layers=[
                    BlinkLayerDef(
                        name="blue status blink",
                        color="#00aaff",
                        intensity=0.75,
                        start_ms=0,
                        duration_ms=1500,
                        speed=3.0,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="blink_double_tap",
            category="Blink",
            description="Short double-pulse indicator.",
            animation=make_animation(
                name="blink_double_tap",
                duration_ms=700,
                mode=LightAnimationMode.ONCE,
                layers=[
                    BlinkLayerDef(
                        name="double tap",
                        color="#ffffff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=450,
                        speed=4.0,
                    ),
                ],
            ),
        ),
    ]


def radial_pulse_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="radial_blue_charge",
            category="Radial Pulse",
            description="Blue charge ring expanding from center.",
            animation=make_animation(
                name="radial_blue_charge",
                duration_ms=900,
                mode=LightAnimationMode.ONCE,
                layers=[
                    RadialPulseLayerDef(
                        name="blue charge ring",
                        color="#00ccff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=900,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=0.75,
                        width=0.16,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="radial_red_blast",
            category="Radial Pulse",
            description="Fast red shockwave blast.",
            animation=make_animation(
                name="radial_red_blast",
                duration_ms=450,
                mode=LightAnimationMode.ONCE,
                layers=[
                    RadialPulseLayerDef(
                        name="red shockwave",
                        color="#ff3030",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=450,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=1.0,
                        width=0.22,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="radial_green_scanner",
            category="Radial Pulse",
            description="Soft green scan wave.",
            animation=make_animation(
                name="radial_green_scanner",
                duration_ms=1600,
                layers=[
                    RadialPulseLayerDef(
                        name="green scan wave",
                        color="#22ff66",
                        intensity=0.75,
                        start_ms=0,
                        duration_ms=1600,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=0.9,
                        width=0.12,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="radial_corner_ping",
            category="Radial Pulse",
            description="Pulse expanding from upper-left corner.",
            animation=make_animation(
                name="radial_corner_ping",
                duration_ms=1000,
                layers=[
                    RadialPulseLayerDef(
                        name="corner ping",
                        color="#ffaa00",
                        intensity=0.9,
                        start_ms=0,
                        duration_ms=1000,
                        center=[0.0, 0.0],
                        radius_from=0.0,
                        radius_to=1.4,
                        width=0.18,
                    ),
                ],
            ),
        ),
    ]


def wipe_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="wipe_left_to_right_blue",
            category="Wipe",
            description="Blue wipe moving left to right.",
            animation=make_animation(
                name="wipe_left_to_right_blue",
                duration_ms=1000,
                mode=LightAnimationMode.ONCE,
                layers=[
                    WipeLayerDef(
                        name="left to right",
                        color="#00aaff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=1000,
                        direction=[1.0, 0.0],
                        width=0.18,
                        speed=1.2,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="wipe_right_to_left_red",
            category="Wipe",
            description="Red wipe moving right to left.",
            animation=make_animation(
                name="wipe_right_to_left_red",
                duration_ms=1000,
                mode=LightAnimationMode.ONCE,
                layers=[
                    WipeLayerDef(
                        name="right to left",
                        color="#ff3030",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=1000,
                        direction=[-1.0, 0.0],
                        width=0.18,
                        speed=1.2,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="wipe_bottom_to_top_green",
            category="Wipe",
            description="Green wipe moving upward.",
            animation=make_animation(
                name="wipe_bottom_to_top_green",
                duration_ms=1100,
                mode=LightAnimationMode.ONCE,
                layers=[
                    WipeLayerDef(
                        name="bottom to top",
                        color="#22ff66",
                        intensity=0.9,
                        start_ms=0,
                        duration_ms=1100,
                        direction=[0.0, -1.0],
                        width=0.2,
                        speed=1.25,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="wipe_diagonal_gold",
            category="Wipe",
            description="Diagonal gold wipe.",
            animation=make_animation(
                name="wipe_diagonal_gold",
                duration_ms=1300,
                mode=LightAnimationMode.ONCE,
                layers=[
                    WipeLayerDef(
                        name="diagonal gold",
                        color="#ffcc33",
                        intensity=0.95,
                        start_ms=0,
                        duration_ms=1300,
                        direction=[1.0, 1.0],
                        width=0.2,
                        speed=1.35,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="wipe_white_sweep_loop",
            category="Wipe",
            description="Looping white scanner sweep.",
            animation=make_animation(
                name="wipe_white_sweep_loop",
                duration_ms=1400,
                layers=[
                    WipeLayerDef(
                        name="white sweep",
                        color="#ffffff",
                        intensity=0.85,
                        start_ms=0,
                        duration_ms=1400,
                        direction=[1.0, 0.0],
                        width=0.1,
                        speed=1.35,
                    ),
                ],
            ),
        ),
    ]


def chase_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="chase_blue_comet",
            category="Chase",
            description="Blue comet chase around indexed LEDs.",
            animation=make_animation(
                name="chase_blue_comet",
                duration_ms=1200,
                layers=[
                    ChaseLayerDef(
                        name="blue comet",
                        color="#00aaff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=1200,
                        width=0.08,
                        speed=1.0,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="chase_white_fast",
            category="Chase",
            description="Fast white chase.",
            animation=make_animation(
                name="chase_white_fast",
                duration_ms=700,
                layers=[
                    ChaseLayerDef(
                        name="fast white chase",
                        color="#ffffff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=700,
                        width=0.06,
                        speed=2.0,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="chase_red_alert",
            category="Chase",
            description="Red alert rotating chase.",
            animation=make_animation(
                name="chase_red_alert",
                duration_ms=900,
                layers=[
                    ChaseLayerDef(
                        name="red alert chase",
                        color="#ff2020",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=900,
                        width=0.12,
                        speed=1.5,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="chase_dual_blue_white",
            category="Chase",
            description="Blue and white offset chase.",
            animation=make_animation(
                name="chase_dual_blue_white",
                duration_ms=1300,
                layers=[
                    ChaseLayerDef(
                        name="blue chase",
                        color="#0088ff",
                        intensity=0.9,
                        start_ms=0,
                        duration_ms=1300,
                        width=0.08,
                        speed=1.0,
                    ),
                    ChaseLayerDef(
                        name="white chase offset",
                        color="#ffffff",
                        intensity=0.8,
                        start_ms=325,
                        duration_ms=1300,
                        width=0.06,
                        speed=1.0,
                    ),
                ],
            ),
        ),
    ]


def sparkle_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="sparkle_white_stars",
            category="Sparkle",
            description="White random star sparkle.",
            animation=make_animation(
                name="sparkle_white_stars",
                duration_ms=1800,
                layers=[
                    SparkleLayerDef(
                        name="white stars",
                        color="#ffffff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=1800,
                        speed=1.0,
                        density=0.12,
                        seed=100,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="sparkle_blue_energy",
            category="Sparkle",
            description="Blue electrical sparkle.",
            animation=make_animation(
                name="sparkle_blue_energy",
                duration_ms=1200,
                layers=[
                    SparkleLayerDef(
                        name="blue energy sparks",
                        color="#00ccff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=1200,
                        speed=2.0,
                        density=0.18,
                        seed=200,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="sparkle_gold_coins",
            category="Sparkle",
            description="Gold coin-like sparkle.",
            animation=make_animation(
                name="sparkle_gold_coins",
                duration_ms=1600,
                layers=[
                    SparkleLayerDef(
                        name="gold sparkle",
                        color="#ffcc00",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=1600,
                        speed=1.5,
                        density=0.15,
                        seed=300,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="sparkle_red_damage",
            category="Sparkle",
            description="Red unstable damage sparks.",
            animation=make_animation(
                name="sparkle_red_damage",
                duration_ms=900,
                layers=[
                    SparkleLayerDef(
                        name="red damage sparks",
                        color="#ff3030",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=900,
                        speed=3.0,
                        density=0.22,
                        seed=400,
                    ),
                ],
            ),
        ),
    ]


def combo_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="charge_up_blue",
            category="Combo",
            description="Expanding charge ring with white chase highlights.",
            animation=make_animation(
                name="charge_up_blue",
                duration_ms=1200,
                mode=LightAnimationMode.ONCE,
                layers=[
                    RadialPulseLayerDef(
                        name="charge ring",
                        color="#00ccff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=900,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=0.8,
                        width=0.16,
                    ),
                    ChaseLayerDef(
                        name="white charge chase",
                        color="#ffffff",
                        intensity=0.85,
                        start_ms=150,
                        duration_ms=1000,
                        width=0.08,
                        speed=2.0,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="success_green_flash",
            category="Combo",
            description="Green success flash with sparkle finish.",
            animation=make_animation(
                name="success_green_flash",
                duration_ms=1000,
                mode=LightAnimationMode.ONCE,
                layers=[
                    BlinkLayerDef(
                        name="green success flash",
                        color="#22ff66",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=450,
                        speed=3.0,
                    ),
                    SparkleLayerDef(
                        name="white finish sparkle",
                        color="#ffffff",
                        intensity=0.85,
                        start_ms=350,
                        duration_ms=650,
                        speed=2.0,
                        density=0.18,
                        seed=500,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="failure_red_fizzle",
            category="Combo",
            description="Red fail blink with fading sparks.",
            animation=make_animation(
                name="failure_red_fizzle",
                duration_ms=1000,
                mode=LightAnimationMode.ONCE,
                layers=[
                    BlinkLayerDef(
                        name="red fail blink",
                        color="#ff2020",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=500,
                        speed=4.0,
                    ),
                    SparkleLayerDef(
                        name="red fizzle",
                        color="#ff6030",
                        intensity=0.8,
                        start_ms=250,
                        duration_ms=750,
                        speed=3.0,
                        density=0.2,
                        seed=600,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="true_jedi_gold_loop",
            category="Combo",
            description="Gold celebration loop inspired by collectible meter effects.",
            animation=make_animation(
                name="true_jedi_gold_loop",
                duration_ms=1800,
                layers=[
                    SolidLayerDef(
                        name="gold base",
                        color="#664400",
                        intensity=0.25,
                        start_ms=0,
                        duration_ms=1800,
                    ),
                    ChaseLayerDef(
                        name="gold chase",
                        color="#ffcc00",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=1800,
                        width=0.08,
                        speed=1.5,
                    ),
                    SparkleLayerDef(
                        name="coin sparkle",
                        color="#ffffff",
                        intensity=0.75,
                        start_ms=0,
                        duration_ms=1800,
                        speed=2.0,
                        density=0.12,
                        seed=700,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="power_core_idle",
            category="Combo",
            description="Subtle idle core with slow pulse and faint sparkle.",
            animation=make_animation(
                name="power_core_idle",
                duration_ms=2200,
                layers=[
                    SolidLayerDef(
                        name="dim blue base",
                        color="#003366",
                        intensity=0.22,
                        start_ms=0,
                        duration_ms=2200,
                    ),
                    RadialPulseLayerDef(
                        name="soft core pulse",
                        color="#00aaff",
                        intensity=0.55,
                        start_ms=0,
                        duration_ms=2200,
                        center=[0.5, 0.5],
                        radius_from=0.1,
                        radius_to=0.7,
                        width=0.24,
                    ),
                    SparkleLayerDef(
                        name="tiny energy flecks",
                        color="#99eeff",
                        intensity=0.5,
                        start_ms=0,
                        duration_ms=2200,
                        speed=0.8,
                        density=0.06,
                        seed=800,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="overheat_warning",
            category="Combo",
            description="Amber-to-red warning made from wipe, blink, and sparkle layers.",
            animation=make_animation(
                name="overheat_warning",
                duration_ms=1400,
                layers=[
                    WipeLayerDef(
                        name="amber heat sweep",
                        color="#ff9900",
                        intensity=0.75,
                        start_ms=0,
                        duration_ms=1400,
                        direction=[1.0, 0.0],
                        width=0.22,
                        speed=1.2,
                    ),
                    BlinkLayerDef(
                        name="red warning pulse",
                        color="#ff2020",
                        intensity=0.9,
                        start_ms=300,
                        duration_ms=1100,
                        speed=3.0,
                    ),
                    SparkleLayerDef(
                        name="hot sparks",
                        color="#ffaa33",
                        intensity=0.85,
                        start_ms=250,
                        duration_ms=1150,
                        speed=2.5,
                        density=0.16,
                        seed=900,
                    ),
                ],
            ),
        ),
    ]