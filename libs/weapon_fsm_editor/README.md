# weapon-fsm-editor

PyQt6 dashboard for viewing and simulating the weapon profile.

## LED preview canvas

The editor now includes a 2D LED preview canvas. When the runtime emits a
`play_light` or `start_light_sequence` command, the editor loads the referenced
light-sequence YAML file and renders the LED layout plus the animated frames.

Supported light-sequence YAML shape:

```yaml
layout:
  width: 640
  height: 220
  background: weapon_outline.png   # optional
  leds:
    - id: muzzle_left
      x: 70
      y: 110
      radius: 12
      label: M1                     # optional
    - id: muzzle_right
      x: 120
      y: 110
      radius: 12

frame_duration_ms: 60               # default for frames, optional
frames:
  - duration_ms: 80                 # optional override per frame
    leds:
      muzzle_left: "#ffcc55"
      muzzle_right:
        color: "#ff9933"
        intensity: 0.7
  - leds:
      muzzle_left:
        color: "#552200"
        intensity: 0.2
      muzzle_right:
        off: true
```

You can also split the overlay layout into a separate YAML file:

```yaml
layout:
  path: light_layout.yaml
frames:
  - leds:
      muzzle_left: "#ffaa33"
```

See `examples/light_layout.yaml` and `examples/muzzle_flash.yaml` for a small
reference pair.


The bundled example ring layout comes from `examples/ring_layout.json`, and `examples/ring_sequence.yaml` shows how to reference it from a sequence file.
