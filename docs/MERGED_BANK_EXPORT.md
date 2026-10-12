# Compiling the complete six-bank library

Run this from the editor project with `uv` dependencies installed and FFmpeg
available on PATH:

    uv run weapon-fsm-export-sd --all-banks --sd-root E:\\

For a minimal Python installation (PyYAML plus FFmpeg, no GUI dependencies):

    PYTHONPATH=src python tools/build_merged_sd.py --sd-root ./sd_staging

The same `compile_bank_library` function backs both paths. It compiles the
original 52 firmware weapon definitions into editable YAML and binary
WFSMBIN1 runtimes, adds C3-PO/Aiai/Metroid Prime/Yoda/Darth Maul examples,
and produces `weapons_manifest.bin` for six banks containing 58 weapons.

The source profiles are under `src/weapon_fsm_workspace/demos/legacy` and the
curated demos are next to it. Lighting uses the `cpx_ring_61_outside_in`
layout, matching physical LED index 0 on the outer ring and index 60 in the
center. All light frames are compiled to WFLSEQ01, with a WFLLAY01 layout.

Deduplication: normalized audio is content-addressed in
`assets/audio/shared/`; compiled sequence+layout pairs are content-addressed
in `assets/lights/shared/`, so weapon profiles can share resources.

Metroid Prime's regular first, second, and third shots trigger the same
`metroid_prime_regular_shot.yaml` 180 ms amber/cyan fade, which is less bright
than the charged release. `heart_heal_red.yaml` is used when C3-PO heals.

Eight original audio references were missing from the supplied source assets.
The `legacy/MISSING_SOURCE_AUDIO.md` manifest lists all substitutes clearly;
replace them with originals if they become available.
