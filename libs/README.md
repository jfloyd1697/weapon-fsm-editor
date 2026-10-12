# weapon_fsm_lights canvas update

This update keeps the existing LED layout/sequence loader and preview widget, then adds a canvas-animation compiler.

## Workflow

1. Load a normalized LED layout JSON.
2. Author a canvas-space animation YAML.
3. Compile the animation by sampling it at each LED point.
4. Preview the compiled per-LED frames in `LedCanvasWidget`.
5. Export compact hardware JSON with `export_hardware_sequence_json`.

## Example

```python
from weapon_fsm_lights import load_canvas_animation_sequence, export_hardware_sequence_json

asset = load_canvas_animation_sequence("examples/charge_glow.canvas.yaml")
export_hardware_sequence_json(asset, "charge_glow.hardware.json")
```

## Layer types

Current compiler layer types:

- `solid`
- `blink`
- `radial_pulse`
- `wipe`
