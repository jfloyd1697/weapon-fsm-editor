# CPX 61-LED ring: selectable physical wiring

The editor now includes two coordinate-identical layouts with different LED index assignments:

- `cpx_ring_61.json` — original inside-out wiring; index 0 is the center LED.
- `cpx_ring_61_outside_in.json` — outside-in wiring; index 0 is on the outer ring, index 60 at center.

The current STM32/CPX build is wired **outside-in**. Its demo sequences
(`idle_glow.yaml`, `rainbow_ring_61.yaml`, `metroid-prime-lights.yaml`) point to
`layouts/cpx_ring_61_outside_in.json`.

When authoring sequences for another wiring order, change `layout.path` to
`layouts/cpx_ring_61.json` and **regenerate the sequence binary** using the SD exporter.
Changing only the compiled layout file will *not* remap precompiled frames.

The angular order of indices within a ring is still unverified on hardware.
