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
        *charge_shot_presets(),
        *metroid_prime_charge_shot_presets(),
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


def charge_shot_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="charge_shot_blue_build",
            category="Charge Shot",
            description="Blue energy builds from the center with a rotating white charge highlight.",
            animation=make_animation(
                name="charge_shot_blue_build",
                duration_ms=1800,
                layers=[
                    SolidLayerDef(
                        name="dim blue core",
                        color="#003366",
                        intensity=0.22,
                        start_ms=0,
                        duration_ms=1800,
                    ),
                    RadialPulseLayerDef(
                        name="expanding blue charge",
                        color="#00aaff",
                        intensity=0.75,
                        start_ms=0,
                        duration_ms=1800,
                        center=[0.5, 0.5],
                        radius_from=0.05,
                        radius_to=0.75,
                        width=0.18,
                    ),
                    ChaseLayerDef(
                        name="white charge orbit",
                        color="#ffffff",
                        intensity=0.75,
                        start_ms=200,
                        duration_ms=1600,
                        width=0.06,
                        speed=2.5,
                    ),
                    SparkleLayerDef(
                        name="blue energy flecks",
                        color="#66ddff",
                        intensity=0.55,
                        start_ms=300,
                        duration_ms=1500,
                        speed=1.6,
                        density=0.10,
                        seed=1100,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="charge_shot_blue_hold",
            category="Charge Shot",
            description="Looping full-charge blue hold with active sparks and rotating highlight.",
            animation=make_animation(
                name="charge_shot_blue_hold",
                duration_ms=1200,
                layers=[
                    SolidLayerDef(
                        name="charged blue base",
                        color="#0066aa",
                        intensity=0.45,
                        start_ms=0,
                        duration_ms=1200,
                    ),
                    RadialPulseLayerDef(
                        name="breathing charged core",
                        color="#00ccff",
                        intensity=0.85,
                        start_ms=0,
                        duration_ms=1200,
                        center=[0.5, 0.5],
                        radius_from=0.25,
                        radius_to=0.65,
                        width=0.28,
                    ),
                    ChaseLayerDef(
                        name="hot white orbit",
                        color="#ffffff",
                        intensity=0.9,
                        start_ms=0,
                        duration_ms=1200,
                        width=0.055,
                        speed=3.0,
                    ),
                    SparkleLayerDef(
                        name="charged sparks",
                        color="#bdf7ff",
                        intensity=0.8,
                        start_ms=0,
                        duration_ms=1200,
                        speed=2.4,
                        density=0.18,
                        seed=1110,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="discharge_shot_blue_blast",
            category="Discharge",
            description="Fast blue-white discharge blast with outward shockwave.",
            animation=make_animation(
                name="discharge_shot_blue_blast",
                duration_ms=650,
                mode=LightAnimationMode.ONCE,
                layers=[
                    SolidLayerDef(
                        name="white muzzle flash",
                        color="#ffffff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=120,
                    ),
                    RadialPulseLayerDef(
                        name="blue shockwave",
                        color="#00ccff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=420,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=1.0,
                        width=0.22,
                    ),
                    WipeLayerDef(
                        name="forward shot streak",
                        color="#66ddff",
                        intensity=1.0,
                        start_ms=80,
                        duration_ms=450,
                        direction=[1.0, 0.0],
                        width=0.16,
                        speed=1.5,
                    ),
                    SparkleLayerDef(
                        name="discharge fragments",
                        color="#ffffff",
                        intensity=0.85,
                        start_ms=120,
                        duration_ms=530,
                        speed=3.2,
                        density=0.22,
                        seed=1120,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="cooldown_shot_blue_fade",
            category="Cooldown",
            description="Blue energy fades after firing with a few residual sparks.",
            animation=make_animation(
                name="cooldown_shot_blue_fade",
                duration_ms=1000,
                mode=LightAnimationMode.ONCE,
                layers=[
                    SolidLayerDef(
                        name="fading blue residue",
                        color="#004477",
                        intensity=0.28,
                        start_ms=0,
                        duration_ms=1000,
                    ),
                    SparkleLayerDef(
                        name="residual blue sparks",
                        color="#66ddff",
                        intensity=0.55,
                        start_ms=0,
                        duration_ms=800,
                        speed=1.6,
                        density=0.08,
                        seed=1130,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="charge_shot_red_unstable_build",
            category="Charge Shot",
            description="Unstable red charge with warning blink and hot sparks.",
            animation=make_animation(
                name="charge_shot_red_unstable_build",
                duration_ms=1600,
                layers=[
                    SolidLayerDef(
                        name="dark red core",
                        color="#440000",
                        intensity=0.3,
                        start_ms=0,
                        duration_ms=1600,
                    ),
                    BlinkLayerDef(
                        name="red warning pulse",
                        color="#ff2020",
                        intensity=0.75,
                        start_ms=200,
                        duration_ms=1400,
                        speed=3.0,
                    ),
                    RadialPulseLayerDef(
                        name="unstable heat ring",
                        color="#ff5522",
                        intensity=0.85,
                        start_ms=0,
                        duration_ms=1600,
                        center=[0.5, 0.5],
                        radius_from=0.1,
                        radius_to=0.8,
                        width=0.16,
                    ),
                    SparkleLayerDef(
                        name="hot unstable sparks",
                        color="#ffaa33",
                        intensity=0.75,
                        start_ms=250,
                        duration_ms=1350,
                        speed=2.6,
                        density=0.2,
                        seed=1200,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="charge_shot_red_critical_hold",
            category="Charge Shot",
            description="Critical charged red hold with fast warning pulse.",
            animation=make_animation(
                name="charge_shot_red_critical_hold",
                duration_ms=900,
                layers=[
                    SolidLayerDef(
                        name="critical red base",
                        color="#660000",
                        intensity=0.42,
                        start_ms=0,
                        duration_ms=900,
                    ),
                    BlinkLayerDef(
                        name="critical red strobe",
                        color="#ff2020",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=900,
                        speed=5.0,
                    ),
                    ChaseLayerDef(
                        name="critical orbit",
                        color="#ffaa33",
                        intensity=0.85,
                        start_ms=0,
                        duration_ms=900,
                        width=0.08,
                        speed=3.0,
                    ),
                    SparkleLayerDef(
                        name="critical sparks",
                        color="#ffffff",
                        intensity=0.75,
                        start_ms=0,
                        duration_ms=900,
                        speed=3.5,
                        density=0.22,
                        seed=1210,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="discharge_shot_red_overload",
            category="Discharge",
            description="Violent red-orange overload discharge.",
            animation=make_animation(
                name="discharge_shot_red_overload",
                duration_ms=700,
                mode=LightAnimationMode.ONCE,
                layers=[
                    SolidLayerDef(
                        name="white-hot overload flash",
                        color="#ffffff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=90,
                    ),
                    RadialPulseLayerDef(
                        name="red overload shockwave",
                        color="#ff2020",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=380,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=1.1,
                        width=0.26,
                    ),
                    WipeLayerDef(
                        name="orange blast streak",
                        color="#ff7a22",
                        intensity=1.0,
                        start_ms=80,
                        duration_ms=420,
                        direction=[1.0, 0.0],
                        width=0.22,
                        speed=1.65,
                    ),
                    SparkleLayerDef(
                        name="overload debris",
                        color="#ffaa33",
                        intensity=1.0,
                        start_ms=100,
                        duration_ms=600,
                        speed=4.0,
                        density=0.26,
                        seed=1220,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="charge_shot_green_plasma_build",
            category="Charge Shot",
            description="Green plasma charge with expanding energy field.",
            animation=make_animation(
                name="charge_shot_green_plasma_build",
                duration_ms=1700,
                layers=[
                    SolidLayerDef(
                        name="green plasma base",
                        color="#003b18",
                        intensity=0.3,
                        start_ms=0,
                        duration_ms=1700,
                    ),
                    RadialPulseLayerDef(
                        name="plasma field growth",
                        color="#22ff66",
                        intensity=0.85,
                        start_ms=0,
                        duration_ms=1700,
                        center=[0.5, 0.5],
                        radius_from=0.08,
                        radius_to=0.82,
                        width=0.2,
                    ),
                    WipeLayerDef(
                        name="plasma sweep",
                        color="#99ffaa",
                        intensity=0.55,
                        start_ms=200,
                        duration_ms=1300,
                        direction=[0.0, -1.0],
                        width=0.18,
                        speed=1.2,
                    ),
                    SparkleLayerDef(
                        name="plasma particles",
                        color="#ccffdd",
                        intensity=0.65,
                        start_ms=250,
                        duration_ms=1450,
                        speed=1.8,
                        density=0.13,
                        seed=1300,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="discharge_shot_green_plasma_lance",
            category="Discharge",
            description="Focused green plasma discharge lance.",
            animation=make_animation(
                name="discharge_shot_green_plasma_lance",
                duration_ms=620,
                mode=LightAnimationMode.ONCE,
                layers=[
                    SolidLayerDef(
                        name="plasma ignition",
                        color="#ccffdd",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=100,
                    ),
                    WipeLayerDef(
                        name="green lance",
                        color="#22ff66",
                        intensity=1.0,
                        start_ms=40,
                        duration_ms=420,
                        direction=[1.0, 0.0],
                        width=0.12,
                        speed=1.8,
                    ),
                    RadialPulseLayerDef(
                        name="plasma recoil ring",
                        color="#99ffaa",
                        intensity=0.85,
                        start_ms=80,
                        duration_ms=400,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=0.85,
                        width=0.18,
                    ),
                    SparkleLayerDef(
                        name="green discharge particles",
                        color="#ffffff",
                        intensity=0.75,
                        start_ms=120,
                        duration_ms=500,
                        speed=3.0,
                        density=0.18,
                        seed=1310,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="charge_shot_gold_hero_build",
            category="Charge Shot",
            description="Heroic gold charge with sparkle and rotating ring.",
            animation=make_animation(
                name="charge_shot_gold_hero_build",
                duration_ms=1900,
                layers=[
                    SolidLayerDef(
                        name="warm gold base",
                        color="#443000",
                        intensity=0.32,
                        start_ms=0,
                        duration_ms=1900,
                    ),
                    RadialPulseLayerDef(
                        name="gold charge aura",
                        color="#ffcc00",
                        intensity=0.9,
                        start_ms=0,
                        duration_ms=1900,
                        center=[0.5, 0.5],
                        radius_from=0.05,
                        radius_to=0.8,
                        width=0.2,
                    ),
                    ChaseLayerDef(
                        name="hero gold orbit",
                        color="#ffffff",
                        intensity=0.8,
                        start_ms=150,
                        duration_ms=1750,
                        width=0.06,
                        speed=2.25,
                    ),
                    SparkleLayerDef(
                        name="hero sparkle",
                        color="#fff2aa",
                        intensity=0.75,
                        start_ms=200,
                        duration_ms=1700,
                        speed=1.7,
                        density=0.16,
                        seed=1400,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="discharge_shot_gold_burst",
            category="Discharge",
            description="Bright gold discharge burst with celebratory sparks.",
            animation=make_animation(
                name="discharge_shot_gold_burst",
                duration_ms=800,
                mode=LightAnimationMode.ONCE,
                layers=[
                    SolidLayerDef(
                        name="gold-white flash",
                        color="#ffffff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=120,
                    ),
                    RadialPulseLayerDef(
                        name="gold burst wave",
                        color="#ffcc00",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=500,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=1.05,
                        width=0.28,
                    ),
                    SparkleLayerDef(
                        name="gold discharge sparkle",
                        color="#fff2aa",
                        intensity=1.0,
                        start_ms=100,
                        duration_ms=700,
                        speed=2.8,
                        density=0.24,
                        seed=1410,
                    ),
                ],
            ),
        ),
    ]


def metroid_prime_charge_shot_presets() -> list[AnimationPreset]:
    return [
        AnimationPreset(
            name="prime_charge_warm_build",
            category="Metroid Prime Charge Shot",
            description=(
                "Warm Metroid Prime-style charge buildup with a yellow-white core, "
                "amber shell, blue residual glow, and small energy flecks."
            ),
            animation=make_animation(
                name="prime_charge_warm_build",
                duration_ms=1900,
                layers=[
                    SolidLayerDef(
                        name="dark cannon glow",
                        color="#1a1206",
                        intensity=0.18,
                        start_ms=0,
                        duration_ms=1900,
                    ),
                    SolidLayerDef(
                        name="warm yellow core",
                        color="#ffe066",
                        intensity=0.34,
                        start_ms=250,
                        duration_ms=1650,
                    ),
                    RadialPulseLayerDef(
                        name="amber charge shell",
                        color="#ffb02e",
                        intensity=0.85,
                        start_ms=0,
                        duration_ms=1900,
                        center=[0.5, 0.5],
                        radius_from=0.08,
                        radius_to=0.70,
                        width=0.25,
                    ),
                    RadialPulseLayerDef(
                        name="white-hot inner ring",
                        color="#fff3b0",
                        intensity=0.72,
                        start_ms=300,
                        duration_ms=1600,
                        center=[0.5, 0.5],
                        radius_from=0.05,
                        radius_to=0.46,
                        width=0.12,
                    ),
                    RadialPulseLayerDef(
                        name="cyan outer shimmer",
                        color="#4ad8ff",
                        intensity=0.45,
                        start_ms=450,
                        duration_ms=1350,
                        center=[0.5, 0.5],
                        radius_from=0.20,
                        radius_to=0.78,
                        width=0.08,
                    ),
                    ChaseLayerDef(
                        name="orange orbit streaks",
                        color="#ff8a22",
                        intensity=0.85,
                        start_ms=250,
                        duration_ms=1650,
                        width=0.07,
                        speed=2.8,
                    ),
                    SparkleLayerDef(
                        name="charge flecks",
                        color="#fff7d6",
                        intensity=0.65,
                        start_ms=350,
                        duration_ms=1500,
                        speed=2.1,
                        density=0.13,
                        seed=2200,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="prime_charge_warm_hold",
            category="Metroid Prime Charge Shot",
            description=(
                "Fully charged warm energy ball: dense yellow core, amber sphere, "
                "cyan rim, and rotating energy flecks."
            ),
            animation=make_animation(
                name="prime_charge_warm_hold",
                duration_ms=1150,
                layers=[
                    SolidLayerDef(
                        name="amber base glow",
                        color="#5a3200",
                        intensity=0.34,
                        start_ms=0,
                        duration_ms=1150,
                    ),
                    SolidLayerDef(
                        name="white-yellow core",
                        color="#fff2a0",
                        intensity=0.48,
                        start_ms=0,
                        duration_ms=1150,
                    ),
                    RadialPulseLayerDef(
                        name="breathing amber shell",
                        color="#ffb02e",
                        intensity=0.95,
                        start_ms=0,
                        duration_ms=1150,
                        center=[0.5, 0.5],
                        radius_from=0.30,
                        radius_to=0.62,
                        width=0.30,
                    ),
                    RadialPulseLayerDef(
                        name="thin cyan edge",
                        color="#4ad8ff",
                        intensity=0.55,
                        start_ms=0,
                        duration_ms=1150,
                        center=[0.5, 0.5],
                        radius_from=0.48,
                        radius_to=0.72,
                        width=0.08,
                    ),
                    ChaseLayerDef(
                        name="fast amber orbit",
                        color="#ffd166",
                        intensity=0.90,
                        start_ms=0,
                        duration_ms=1150,
                        width=0.055,
                        speed=3.4,
                    ),
                    SparkleLayerDef(
                        name="charged white sparks",
                        color="#ffffff",
                        intensity=0.78,
                        start_ms=0,
                        duration_ms=1150,
                        speed=2.8,
                        density=0.18,
                        seed=2210,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="prime_charge_warm_release",
            category="Metroid Prime Charge Shot",
            description=(
                "Metroid Prime-style release: white flash, golden core burst, "
                "amber shockwave, cyan rim, and short forward bolt."
            ),
            animation=make_animation(
                name="prime_charge_warm_release",
                duration_ms=720,
                mode=LightAnimationMode.ONCE,
                layers=[
                    SolidLayerDef(
                        name="white release flash",
                        color="#ffffff",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=80,
                    ),
                    SolidLayerDef(
                        name="gold blast core",
                        color="#ffd34d",
                        intensity=0.95,
                        start_ms=0,
                        duration_ms=160,
                    ),
                    RadialPulseLayerDef(
                        name="amber shock sphere",
                        color="#ff9f1a",
                        intensity=1.0,
                        start_ms=0,
                        duration_ms=440,
                        center=[0.5, 0.5],
                        radius_from=0.0,
                        radius_to=1.05,
                        width=0.30,
                    ),
                    RadialPulseLayerDef(
                        name="cyan shock rim",
                        color="#4ad8ff",
                        intensity=0.75,
                        start_ms=30,
                        duration_ms=390,
                        center=[0.5, 0.5],
                        radius_from=0.05,
                        radius_to=1.0,
                        width=0.09,
                    ),
                    WipeLayerDef(
                        name="forward blue-white bolt",
                        color="#9beeff",
                        intensity=1.0,
                        start_ms=40,
                        duration_ms=420,
                        direction=[1.0, 0.0],
                        width=0.13,
                        speed=1.85,
                    ),
                    SparkleLayerDef(
                        name="gold-white fragments",
                        color="#fff7d6",
                        intensity=0.95,
                        start_ms=90,
                        duration_ms=540,
                        speed=3.4,
                        density=0.22,
                        seed=2220,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="prime_charge_warm_cooldown",
            category="Metroid Prime Charge Shot",
            description=(
                "Post-shot cooldown with fading amber residue and a few cyan-white sparks."
            ),
            animation=make_animation(
                name="prime_charge_warm_cooldown",
                duration_ms=950,
                mode=LightAnimationMode.ONCE,
                layers=[
                    SolidLayerDef(
                        name="fading amber residue",
                        color="#5a3200",
                        intensity=0.25,
                        start_ms=0,
                        duration_ms=950,
                    ),
                    RadialPulseLayerDef(
                        name="small fading ring",
                        color="#ffb02e",
                        intensity=0.45,
                        start_ms=0,
                        duration_ms=650,
                        center=[0.5, 0.5],
                        radius_from=0.25,
                        radius_to=0.55,
                        width=0.18,
                    ),
                    SparkleLayerDef(
                        name="cooldown flecks",
                        color="#9beeff",
                        intensity=0.45,
                        start_ms=0,
                        duration_ms=850,
                        speed=1.5,
                        density=0.08,
                        seed=2230,
                    ),
                ],
            ),
        ),
        AnimationPreset(
            name="prime_charge_dark_ring_hold",
            category="Metroid Prime Charge Shot",
            description=(
                "Lit amber charge sphere with an inverted radial ring cutting through it."
            ),
            animation=make_animation(
                name="prime_charge_dark_ring_hold",
                duration_ms=1200,
                layers=[
                    SolidLayerDef(
                        name="amber charge field",
                        color="#ffb02e",
                        intensity=0.75,
                        start_ms=0,
                        duration_ms=1200,
                        mask_enabled=True,
                        mask_center=[0.5, 0.5],
                        mask_radius=0.72,
                        mask_softness=0.12,
                    ),
                    SolidLayerDef(
                        name="white hot core",
                        color="#fff2a0",
                        intensity=0.45,
                        start_ms=0,
                        duration_ms=1200,
                        mask_enabled=True,
                        mask_center=[0.5, 0.5],
                        mask_radius=0.35,
                        mask_softness=0.10,
                    ),
                    RadialPulseLayerDef(
                        name="dark outward ring",
                        color="#000000",
                        intensity=0.9,
                        start_ms=0,
                        duration_ms=1200,
                        center=[0.5, 0.5],
                        radius_from=0.15,
                        radius_to=0.72,
                        width=0.12,
                        invert=True,
                        mask_enabled=True,
                        mask_center=[0.5, 0.5],
                        mask_radius=0.75,
                        mask_softness=0.08,
                    ),
                    SparkleLayerDef(
                        name="edge sparks",
                        color="#fff7d6",
                        intensity=0.65,
                        start_ms=0,
                        duration_ms=1200,
                        speed=2.4,
                        density=0.12,
                        seed=2240,
                        mask_enabled=True,
                        mask_center=[0.5, 0.5],
                        mask_radius=0.78,
                        mask_softness=0.05,
                    ),
                ],
            ),
        )
    ]