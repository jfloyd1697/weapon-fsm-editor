"""Prepare audio files for the STM32 I2S streaming backend.

The MCU consumes little-endian, 16-bit PCM at a fixed 44.1 kHz sample rate.
Always normalize during export so authored clips can have arbitrary sample rates,
channel counts, or encodings without requiring an embedded audio decoder.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


RUNTIME_AUDIO_SAMPLE_RATE = 44_100
RUNTIME_AUDIO_CHANNELS = 1
RUNTIME_AUDIO_CODEC = "pcm_s16le"


def export_audio_wav(source: Path, destination: Path) -> None:
    """Convert one authored sound into MCU-compatible PCM WAV, atomically.

    ffmpeg is a required SD-export tool, not a runtime firmware dependency.
    Keeping the original clip untouched allows repeatable re-exports.
    """
    executable = shutil.which("ffmpeg")
    if executable is None:
        raise RuntimeError(
            "SD audio export requires ffmpeg on PATH to create 44.1 kHz, "
            "16-bit PCM WAV files. Install ffmpeg and retry."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".audio-", suffix=".wav", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        command = [
            executable,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(source),
            "-map", "0:a:0",
            "-vn",
            "-ac", str(RUNTIME_AUDIO_CHANNELS),
            "-ar", str(RUNTIME_AUDIO_SAMPLE_RATE),
            "-c:a", RUNTIME_AUDIO_CODEC,
            "-f", "wav",
            str(temporary),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            error = result.stderr.strip() or f"ffmpeg exited with code {result.returncode}"
            raise ValueError(f"Could not convert audio clip '{source}': {error}")
        if temporary.stat().st_size == 0:
            raise ValueError(f"Converted audio clip is empty: {source}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
