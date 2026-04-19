from __future__ import annotations

from pathlib import Path

from libs.asset_integration.compile.path_resolution import resolve_asset_path
from libs.asset_integration.model.actions import (
    ActionDef,
    PlayAudioActionDef,
    PlayLightActionDef,
    StopAudioActionDef,
    StopLightActionDef,
)
from libs.asset_integration.model.weapon import WeaponDef
from libs.asset_integration.runtime.commands import (
    GunRuntimeCommand,
    PlayAudioCommand,
    PlayLightCommand,
    StopAudioCommand,
    StopLightCommand,
)


class CompileError(ValueError):
    pass


def compile_action(action: ActionDef, weapon: WeaponDef, weapon_file: str | Path) -> GunRuntimeCommand:
    if isinstance(action, PlayAudioActionDef):
        clip = weapon.clips.get(action.clip)
        if clip is None:
            raise CompileError(f"Unknown clip: {action.clip!r}")
        return PlayAudioCommand(
            clip_name=clip.name,
            resolved_path=str(resolve_asset_path(weapon_file, clip.path)),
            mode=action.mode,
            interrupt=action.interrupt,
            channel=action.channel,
            gain=1.0 if action.gain is None else float(action.gain),
        )

    if isinstance(action, StopAudioActionDef):
        return StopAudioCommand(
            clip_name=action.clip,
            channel=action.channel,
        )

    if isinstance(action, PlayLightActionDef):
        sequence = weapon.light_sequences.get(action.sequence)
        if sequence is None:
            raise CompileError(f"Unknown light sequence: {action.sequence!r}")
        return PlayLightCommand(
            sequence_name=sequence.name,
            resolved_path=str(resolve_asset_path(weapon_file, sequence.path)),
            mode=action.mode,
            target=action.target,
        )

    if isinstance(action, StopLightActionDef):
        return StopLightCommand(
            sequence_name=action.sequence,
            target=action.target,
        )

    raise CompileError(f"Unsupported action type: {type(action)!r}")
