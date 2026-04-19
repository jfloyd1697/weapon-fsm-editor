from __future__ import annotations

from typing import Any

import yaml

from libs.asset_integration.model.actions import (
    ActionDef,
    PlayAudioActionDef,
    PlayLightActionDef,
    StopAudioActionDef,
    StopLightActionDef,
)
from libs.asset_integration.model.assets import ClipDef, LightSequenceDef
from libs.asset_integration.model.weapon import StateDef, TransitionDef, WeaponDef


class ParseError(ValueError):
    pass


VALID_ACTION_TYPES = {
    "play_audio",
    "stop_audio",
    "play_light",
    "stop_light",
}


def parse_weapon_yaml(text: str) -> WeaponDef:
    raw = yaml.safe_load(text) or {}
    weapon_raw = raw.get("weapon") or {}

    clips = {
        name: ClipDef(name=name, path=data["path"], preload=bool(data.get("preload", True)))
        for name, data in (raw.get("clips") or {}).items()
    }
    light_sequences = {
        name: LightSequenceDef(name=name, path=data["path"], preload=bool(data.get("preload", True)))
        for name, data in (raw.get("light_sequences") or {}).items()
    }

    states = [
        StateDef(
            id=item["id"],
            label=item.get("label"),
            on_entry=[parse_action(action) for action in item.get("on_entry", [])],
            on_exit=[parse_action(action) for action in item.get("on_exit", [])],
        )
        for item in raw.get("states", [])
    ]

    transitions = [
        TransitionDef(
            id=item["id"],
            source=item["source"],
            trigger=item["trigger"],
            target=item["target"],
            guard=item.get("guard"),
            actions=[parse_action(action) for action in item.get("actions", [])],
        )
        for item in raw.get("transitions", [])
    ]

    return WeaponDef(
        initial_state=weapon_raw["initial_state"],
        variables=dict(weapon_raw.get("variables", {})),
        clips=clips,
        light_sequences=light_sequences,
        states=states,
        transitions=transitions,
    )


def parse_action(raw: dict[str, Any]) -> ActionDef:
    action_type = raw.get("type")
    if action_type not in VALID_ACTION_TYPES:
        raise ParseError(f"Unsupported action type: {action_type!r}")

    if action_type == "play_audio":
        return PlayAudioActionDef(
            clip=raw["clip"],
            mode=raw.get("mode", "one_shot"),
            interrupt=raw.get("interrupt", "restart"),
            channel=raw.get("channel"),
            gain=raw.get("gain"),
        )
    if action_type == "stop_audio":
        return StopAudioActionDef(
            clip=raw.get("clip"),
            channel=raw.get("channel"),
        )
    if action_type == "play_light":
        return PlayLightActionDef(
            sequence=raw["sequence"],
            mode=raw.get("mode", "one_shot"),
            target=raw.get("target"),
        )
    if action_type == "stop_light":
        return StopLightActionDef(
            sequence=raw.get("sequence"),
            target=raw.get("target"),
        )

    raise ParseError(f"Unhandled action type: {action_type!r}")
