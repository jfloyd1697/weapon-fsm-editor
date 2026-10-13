# Weapon equip audio and lighting

All SD-compiled weapons use the outside-in 61-LED `cpx_ring_61_outside_in` physical layout.
The exporter preserves the authoring YAML and writes the referenced sequences as binary
assets under `assets/lights/shared/`.

- Metroid Prime: `metroid_prime.yaml` -> `prime_equip_radial` (476 ms). The amber/cyan
  pulse expands from the center (LED 60) to the outside (LEDs 0–23) and contracts
  back inward, played with the existing equip WAV when `on_equip` transitions to
  `equipping`. The previous `stop_light` action is retained before the new pulse.
- LEGO characters: the eight legacy character profiles and three curated C-3PO,
  Yoda, Darth Maul profiles use the real LEGO switch-character WAV and a 560 ms
  colored left-to-right wipe. The wipe fades out at the end. The legacy profiles
  use their existing `equip` state's `on_entry`. The curated profiles use an
  internal `on_equip` transition from `alive`.
- `true_jedi` is a separate LEGO score/charge effect rather than a character
  and does not receive a character-change wipe.
- Every other state machine and gameplay clip remains unchanged.

On every weapon or bank change `Blaster::equipCurrentWeapon()` stops the existing
hardware audio and LED sequence, destroys the old controller (discarding scheduled
FSM events), then loads and initializes the new weapon. It also performs cleanup
if the selected weapon is missing or invalid.

## Recompile and deploy

Run from the editor repository with its dependencies installed:

```powershell
uv run weapon-fsm-export-sd --all-banks --sd-root E:\
```

**Remove the old** `assets/weapons`, `assets/audio/shared`, and
`assets/lights/shared` directories on the SD card before extracting a fresh
compiled export. The binary index is `assets/weapons/weapons_manifest.bin`.

## Regression tests

`tests/test_equip_effects.py` verifies the authoring profile paths, 61-LED
animation contents, Prime pulse direction, and all character equip triggers.
The firmware `WeaponSwitchCleanupTest` verifies that switching to Prime, C-3PO,
Yoda, or Maul always stops old audio and lights before new effects start,
including when an invalid weapon is selected.
