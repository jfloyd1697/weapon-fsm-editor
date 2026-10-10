# SD card export (binary embedded assets)

The authoring tools use YAML for weapon FSMs and animations and may use JSON for
light layouts. **The firmware does not parse YAML or JSON.** The SD exporter
compiles the authoring files to versioned little-endian binary assets and
normalizes audio for the STM32 I2S backend.

Run from the editor workspace:

```powershell
uv run weapon-fsm-export-sd --sd-root E:\ --bank Default
```

With no positional arguments, the command exports every YAML profile from the
workspace `src/weapon_fsm_workspace/demos` directory. To export specific profiles:

```powershell
uv run weapon-fsm-export-sd --sd-root E:\ --bank Default src/weapon_fsm_workspace/demos/metroid_prime.yaml
```

Prefer an **empty SD staging directory** for a complete rebuild; this avoids
retaining unreferenced assets from older versions. The exporter merges repeated
exports into an existing binary manifest and removes the previous JSON manifest.
Failed profiles are printed and cause a nonzero process exit code.

Output:

```text
assets/
  weapons/
    weapons_manifest.bin          # WFMAN001, bank and weapon path index
    Default/
      metroid_prime/
        weapon.bin                # WFSMBIN1, compiled FSM
        audio/*.wav               # exported as 44.1 kHz, 16-bit mono PCM
        lights/
          sequence-name.bin       # WFLSEQ01, packed RGB and per-frame durations
          sequence-name.layout.bin # WFLLAY01, LED index and normalized geometry
```

The exporter requires **ffmpeg** available on PATH. All authored sound formats
are converted to 44,100 Hz, mono, 16-bit signed PCM WAV at export time.
Original audio files are never changed. This avoids MCU-side resampling,
unsupported sample-rate failures, and differences between authored WAV encodings.

The firmware checks the binary manifest and asset references at startup. It
only loads the active weapon's FSM, and the light engine streams one animation
frame at a time from the SD card using bounded reads. No complete sequence is
held in RAM. Legacy JSON runtime files are rejected, not silently parsed.

Binary format v1:

- `WFMAN001`: eight-byte magic, `uint16 version`, `uint16 bank_count`, repeated
  UTF-8 bank name (`uint16 length + bytes`), `uint16 weapon_count`, UTF-8 relative paths.
- `WFLSEQ01`: magic, `uint16 version`, `uint16 led_count`, `uint32 frame_count`,
  `uint32 total_duration_ms`; repeated frames contain `uint32 duration_ms`,
  `uint16 pixel_count` and pixels as `uint16 index`, RGB888 and `uint8 intensity`.
- `WFLLAY01`: magic, `uint16 version`, `uint16 led_count`; each LED record is
  `uint16 index`, normalized `float32 u`, `float32 v`, `float32 radius`.

The Python encoder and C++ reader are cross-tested using committed binary
fixtures in firmware `tests/data/compiled_assets`.
