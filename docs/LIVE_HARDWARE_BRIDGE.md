# Live Hardware Bridge — Weapon FSM Editor

The main toolbar includes **Live Hardware**. Install the project with its new `pyserial` dependency, connect the STM32 USB CDC port (for example COM5), and select one of three modes:

1. **Deploy / device inputs**: choose a complete compiled SD-export folder containing `assets/` and transfer all files. Device validates CRC32 for each `.upload` file, commits it, then reloads the bank/weapon index. The separate **Compile edited weapon and deploy** control compiles the current editor document to a temporary export (without overwriting source YAML), uploads its assets, and reloads the MCU; the weapon's existing bank/manifest entry must already exist. Choose the correct bank in the editor dialog.
2. **PC input / MCU FSM**: press/hold trigger, next/previous weapon, or tap Reload in the editor. Physical MCU buttons are ignored. MCU performs debounce, timers, transitions, and audio/light actions. The editor can send button commands and read acknowledged protocol responses. Button tap duration is 65 ms, allowing the 20 ms core debouncer to detect it.
3. **PC FSM / hardware outputs**: the PC editor's existing `SimulationService` handles external events, state transitions, variables and scheduled actions. Audio commands are sent to the MCU as SD asset paths; LED preview frames are converted to physical-index RGB and streamed to the STM32 on each frame change. This uses the existing simulated editor timing and MCU hardware output timing; no extra MCU FSM or animation renderer.

The Hardware Bridge dialog exposes direct `PLAY_AUDIO`, `PLAY_LIGHT`, STOP and input controls and logs protocol responses. Note that SD files must be deployed first for audio and precompiled sequence playback. Use local mode for deployment.

## Protocol and validation

Client: `weapon_fsm_workspace.hardware_bridge.client.BridgeClient`. Test: `tests/test_hardware_bridge.py`. Binary framing uses 0xA5 0x5A, length, opcode, sequence, payload, CRC16-CCITT. Deployment uses CRC32 verification, temporary files, and explicit runtime activation. The firmware agent and Python client share identical opcodes.

## Dependencies / testing

- PySerial >=3.5 is included in `pyproject.toml`.
- The frame codec and CRC tests have no third-party requirements.
- Full editor GUI smoke testing requires PyQt6 and workspace dependencies; not available in the Linux test container.

## Hardware notes

- Close `pio device monitor` before opening COM5 in the editor.
- Press **Activate selected mode** after connecting. Mode 2 and Mode 3 time out to normal mode if the PC disconnects.
- The STM32 implementation has the complete control plane. Other boards still need their transport and storage adapter connected.

## SD file browser and change-only deploy

**The STM32 firmware must support binary protocol v2.** Earlier firmware used a text-based
USB bridge; the editor cannot transfer files to that version. Connect via the normal USB
CDC COM port, leaving the blaster in **LOCAL** mode for file management.

The Live Hardware dialog now offers an SD browser with folder navigation, upload, download,
new directory, rename, and delete. **Sync folder** transfers local directory contents under
the visible remote path, skipping files whose size and CRC32 match the SD copy. Unrelated
remote files are left intact. **Deploy compiled assets directory** performs the same
change-only upload and activates the compiled bank/weapon afterwards. Individual file
uploads and downloads report progress and verify file contents.

During file operations the MCU pauses weapon control, audio playback, and lighting so it
can safely own the FAT filesystem exclusively. The session is released after browsing or
downloading, and after uploads the active weapon is reloaded. The device also times out
abandoned sessions. Windows sees a serial device, **not** an MSC drive letter.

Upload is staged at `<destination>.upload`, verified using CRC32, then installed with
an old-file backup and rollback on rename failure. Unplugging during a FAT rename or
losing power is not fully atomic; the MCU recovers stale backup/staging files when that
path is next uploaded. Avoid unplugging the USB or power during deployment.
