from dataclasses import dataclass, field
from typing import Iterable

from weapon_fsm_core.domain.commands import GunRuntimeCommand, RuntimeCommand
from weapon_fsm_hardware import RuntimeCommandDispatcher


@dataclass
class RuntimeCommandBridge:
    dispatcher: RuntimeCommandDispatcher
    command_log: list[str] = field(default_factory=list)

    def dispatch_commands(self, commands: Iterable[RuntimeCommand]) -> None:
        for command in commands:
            if not isinstance(command, GunRuntimeCommand):
                continue
            self.dispatcher.dispatch(command)
            self.command_log.append(f"{command.type}: {command.payload}")

    def reset(self) -> None:
        if self.dispatcher.audio is not None:
            self.dispatcher.audio.stop_audio()
        if self.dispatcher.lights is not None:
            self.dispatcher.lights.stop_light()
        self.command_log.clear()
