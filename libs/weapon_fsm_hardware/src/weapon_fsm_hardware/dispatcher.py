import warnings
from dataclasses import dataclass

from weapon_fsm_core.domain.commands import GunRuntimeCommand

from .backends import AudioBackend, LightBackend


@dataclass
class RuntimeCommandDispatcher:
    audio: AudioBackend | None = None
    lights: LightBackend | None = None

    def dispatch(self, command: GunRuntimeCommand) -> None:
        payload = command.payload
        print(command)

        if command.type == "play_audio" and self.audio is not None:
            self.audio.play_audio(
                clip=str(payload.get("clip", "")),
                path=str(payload.get("path", payload.get("clip", ""))),
                mode=str(payload.get("mode", "one_shot")),
                interrupt=str(payload.get("interrupt", "interrupt")),
            )
            return

        elif command.type == "stop_audio" and self.audio is not None:
            self.audio.stop_audio()
            return

        elif command.type == "play_light" and self.lights is not None:
            self.lights.play_light(
                sequence=str(payload.get("sequence", "")),
                path=str(payload.get("path", payload.get("sequence", ""))),
                mode=str(payload.get("mode", "one_shot")),
            )
            return

        elif command.type == "stop_light" and self.lights is not None:
            self.lights.stop_light()
            return

        else:
            warnings.warn(f"Unknown command type: {command}")