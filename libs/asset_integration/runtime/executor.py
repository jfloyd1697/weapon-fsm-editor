from __future__ import annotations

from libs.asset_integration.runtime.commands import (
    GunRuntimeCommand,
    PlayAudioCommand,
    PlayLightCommand,
    StopAudioCommand,
    StopLightCommand,
)
from libs.asset_integration.services.audio_backend import AudioBackend
from libs.asset_integration.services.light_backend import LightBackend


class GunRuntimeCommandExecutor:
    def __init__(
        self,
        audio_backend: AudioBackend | None = None,
        light_backend: LightBackend | None = None,
    ) -> None:
        self._audio_backend = audio_backend
        self._light_backend = light_backend

    def execute(self, command: GunRuntimeCommand) -> None:
        if isinstance(command, PlayAudioCommand):
            if self._audio_backend is not None:
                self._audio_backend.play(
                    command.clip_name,
                    command.resolved_path,
                    mode=command.mode,
                    interrupt=command.interrupt,
                    channel=command.channel,
                    gain=command.gain,
                )
            return

        if isinstance(command, StopAudioCommand):
            if self._audio_backend is not None:
                self._audio_backend.stop(
                    clip_name=command.clip_name,
                    channel=command.channel,
                )
            return

        if isinstance(command, PlayLightCommand):
            if self._light_backend is not None:
                self._light_backend.play(
                    command.sequence_name,
                    command.resolved_path,
                    mode=command.mode,
                    target=command.target,
                )
            return

        if isinstance(command, StopLightCommand):
            if self._light_backend is not None:
                self._light_backend.stop(
                    sequence_name=command.sequence_name,
                    target=command.target,
                )
            return

        raise TypeError(f"Unsupported command type: {type(command)!r}")
