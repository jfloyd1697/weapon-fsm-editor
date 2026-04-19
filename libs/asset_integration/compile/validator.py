from __future__ import annotations

from pathlib import Path

from libs.asset_integration.compile.issues import ValidationIssue
from libs.asset_integration.compile.path_resolution import resolve_asset_path
from libs.asset_integration.model.actions import (
    PlayAudioActionDef,
    PlayLightActionDef,
    StopAudioActionDef,
    StopLightActionDef,
)
from libs.asset_integration.model.weapon import WeaponDef

_VALID_AUDIO_MODES = {"one_shot", "loop"}
_VALID_INTERRUPT_MODES = {"restart", "ignore", "schedule"}
_VALID_LIGHT_MODES = {"one_shot", "loop"}


def validate_weapon(weapon: WeaponDef, weapon_file: str | Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    state_ids = {state.id for state in weapon.states}
    if weapon.initial_state not in state_ids:
        issues.append(
            ValidationIssue(
                path="weapon.initial_state",
                message=f"Unknown initial state {weapon.initial_state!r}",
            )
        )

    for clip_name, clip in weapon.clips.items():
        resolved = resolve_asset_path(weapon_file, clip.path)
        if not resolved.exists():
            issues.append(
                ValidationIssue(
                    path=f"clips.{clip_name}.path",
                    message=f"Clip file does not exist: {resolved}",
                )
            )

    for sequence_name, sequence in weapon.light_sequences.items():
        resolved = resolve_asset_path(weapon_file, sequence.path)
        if not resolved.exists():
            issues.append(
                ValidationIssue(
                    path=f"light_sequences.{sequence_name}.path",
                    message=f"Light sequence file does not exist: {resolved}",
                )
            )

    for state_index, state in enumerate(weapon.states):
        issues.extend(_validate_actions(state.on_entry, weapon, prefix=f"states[{state_index}].on_entry"))
        issues.extend(_validate_actions(state.on_exit, weapon, prefix=f"states[{state_index}].on_exit"))

    for transition_index, transition in enumerate(weapon.transitions):
        if transition.source not in state_ids:
            issues.append(
                ValidationIssue(
                    path=f"transitions[{transition_index}].source",
                    message=f"Unknown source state {transition.source!r}",
                )
            )
        if transition.target not in state_ids:
            issues.append(
                ValidationIssue(
                    path=f"transitions[{transition_index}].target",
                    message=f"Unknown target state {transition.target!r}",
                )
            )
        issues.extend(_validate_actions(transition.actions, weapon, prefix=f"transitions[{transition_index}].actions"))

    return issues


def _validate_actions(actions: list[object], weapon: WeaponDef, prefix: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, action in enumerate(actions):
        path = f"{prefix}[{index}]"

        if isinstance(action, PlayAudioActionDef):
            if action.clip not in weapon.clips:
                issues.append(ValidationIssue(path=f"{path}.clip", message=f"Unknown clip {action.clip!r}"))
            if action.mode not in _VALID_AUDIO_MODES:
                issues.append(ValidationIssue(path=f"{path}.mode", message=f"Invalid audio mode {action.mode!r}"))
            if action.interrupt not in _VALID_INTERRUPT_MODES:
                issues.append(
                    ValidationIssue(path=f"{path}.interrupt", message=f"Invalid interrupt mode {action.interrupt!r}")
                )
            if action.gain is not None and action.gain < 0:
                issues.append(ValidationIssue(path=f"{path}.gain", message="Gain must be >= 0"))

        elif isinstance(action, StopAudioActionDef):
            if action.clip is None and action.channel is None:
                # Intentionally allowed as "stop all audio".
                pass

        elif isinstance(action, PlayLightActionDef):
            if action.sequence not in weapon.light_sequences:
                issues.append(
                    ValidationIssue(path=f"{path}.sequence", message=f"Unknown light sequence {action.sequence!r}")
                )
            if action.mode not in _VALID_LIGHT_MODES:
                issues.append(ValidationIssue(path=f"{path}.mode", message=f"Invalid light mode {action.mode!r}"))

        elif isinstance(action, StopLightActionDef):
            if action.sequence is None and action.target is None:
                # Intentionally allowed as "stop all lights".
                pass

    return issues
