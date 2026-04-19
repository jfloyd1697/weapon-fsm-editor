from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EditorAudioBackend:
    """Simple editor-facing backend stub.

    Replace the internals with QtMultimedia, pygame, sounddevice, etc.
    The interface is stable enough for editor/runtime integration now.
    """

    loaded_paths: dict[str, str] = field(default_factory=dict)
    channel_to_clip: dict[str, str] = field(default_factory=dict)
    last_event: str | None = None

    def preload(self, clip_name: str, path: str) -> None:
        self.loaded_paths[clip_name] = str(Path(path))
        self.last_event = f"preload:{clip_name}"

    def play(
        self,
        clip_name: str,
        path: str,
        *,
        mode: str,
        interrupt: str,
        channel: str | None,
        gain: float,
    ) -> None:
        self.loaded_paths.setdefault(clip_name, str(Path(path)))
        if channel is not None:
            self.channel_to_clip[channel] = clip_name
        self.last_event = (
            f"play clip={clip_name} mode={mode} interrupt={interrupt} "
            f"channel={channel} gain={gain}"
        )

    def stop(self, *, clip_name: str | None = None, channel: str | None = None) -> None:
        if channel is not None:
            self.channel_to_clip.pop(channel, None)
        elif clip_name is not None:
            to_remove = [name for name, current in self.channel_to_clip.items() if current == clip_name]
            for name in to_remove:
                self.channel_to_clip.pop(name, None)
        else:
            self.channel_to_clip.clear()
        self.last_event = f"stop clip={clip_name} channel={channel}"

    def stop_all(self) -> None:
        self.channel_to_clip.clear()
        self.last_event = "stop_all"
