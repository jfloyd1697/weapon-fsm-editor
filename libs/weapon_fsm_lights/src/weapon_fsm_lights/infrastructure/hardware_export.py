from pathlib import Path
import json

from weapon_fsm_lights.infrastructure.loader import LightSequenceAsset


def export_hardware_sequence_json(asset: LightSequenceAsset, path: str | Path) -> None:
    output_path = Path(path)
    ordered_leds = sorted(asset.leds, key=lambda led: led.index if led.index is not None else 0)
    led_index_by_id = {
        led.id: led.index if led.index is not None else index
        for index, led in enumerate(ordered_leds)
    }

    frames = []
    for frame in asset.frames:
        pixels = []
        for led_id, state in frame.leds.items():
            color, intensity = state
            pixels.append(
                {
                    "index": led_index_by_id[led_id],
                    "color": color,
                    "intensity": intensity,
                }
            )
        frames.append({"duration_ms": frame.duration_ms, "pixels": pixels})

    payload = {
        "format": "weapon_fsm_led_sequence_v1",
        "led_count": len(asset.leds),
        "frames": frames,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
