"""Preflight checks for binaries consumed by the firmware weapon controller.

Validate the runtime payload before writing any SD assets. This deliberately
checks the firmware's actual action vocabulary and reference tables, rather
than accepting arbitrary editor actions that the MCU would silently ignore.
"""

from __future__ import annotations

from typing import Any


KNOWN_ACTIONS = frozenset({
    "play_audio", "play_audio_loop", "play_random_audio", "play_audio_effect",
    "stop_audio", "play_light", "stop_light",
    "start_light_sequence", "stop_light_sequence", "set_var", "add_var",
    "adjust_ammo", "set_ammo", "set_ammo_full", "emit_event",
    "schedule_event", "cancel_scheduled_events", "chance_event", "log",
})


def normalize_action_payload(action_type: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Map supported legacy editor spellings to firmware action names."""
    action_type = "play_audio" if action_type == "play_sound" else action_type
    return {"type": action_type, **arguments}


def normalize_runtime_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Rewrite legacy editor actions into supported compiled audio actions.

    One-clip sound sets use play_audio; multi-clip sets use play_random_audio.
    Missing or non-random sets fail preflight rather than silently changing behavior.
    """
    sets = payload.get("clip_sets") or {}

    def normalize(actions: list[dict[str, Any]]) -> None:
        for action in actions:
            kind = action.get("type")
            if kind == "play_sound":
                action["type"] = "play_audio"
            elif kind == "play_sound_random":
                name = action.pop("clip_set", None)
                group = sets.get(name)
                if group is None or group.get("mode", "random") != "random":
                    raise ValueError(f"Unsupported audio clip set {name!r}")
                clips = list(group.get("clips") or [])
                if not clips:
                    raise ValueError(f"Empty audio clip set {name!r}")
                if len(clips) == 1:
                    action["type"] = "play_audio"
                    action["clip"] = clips[0]
                else:
                    action["type"] = "play_random_audio"
                    action["clips"] = clips

    for state in payload.get("states") or []:
        normalize(state.get("on_entry") or [])
        normalize(state.get("on_exit") or [])
    for transition in payload.get("transitions") or []:
        normalize(transition.get("actions") or [])
    return payload


def validate_runtime_payload(payload: dict[str, Any]) -> list[str]:
    """Return all errors that would make an exported weapon unusable."""
    issues: list[str] = []
    states = payload.get("states") or []
    state_ids = {state.get("id") for state in states}
    clips = set(payload.get("clips") or {})
    clip_sets = payload.get("clip_sets") or {}
    effects = payload.get("audio_effects") or {}
    sequences = set(payload.get("light_sequences") or {})

    if not states:
        issues.append("states must not be empty (gun-only profiles are not weapons)")
    if payload.get("initial_state") not in state_ids:
        issues.append("initial_state does not reference a state")

    def check_clip(clip: Any, location: str) -> None:
        if not isinstance(clip, str) or clip not in clips:
            issues.append(f"{location}: unknown clip {clip!r}")

    def check_actions(actions: list[dict[str, Any]], location: str) -> None:
        for index, action in enumerate(actions):
            where = f"{location}[{index}]"
            kind = action.get("type")
            if kind not in KNOWN_ACTIONS:
                issues.append(f"{where}: unknown action type {kind!r}")
            if kind in ("play_audio", "play_audio_loop"):
                check_clip(action.get("clip"), where)
            elif kind == "play_random_audio":
                if not action.get("clips"):
                    issues.append(f"{where}: play_random_audio requires clips")
                for clip in action.get("clips") or []:
                    check_clip(clip, where)
            elif kind == "play_audio_effect":
                if action.get("effect") not in effects:
                    issues.append(f"{where}: unknown audio effect {action.get('effect')!r}")
            elif kind in ("play_light", "start_light_sequence"):
                if action.get("sequence") not in sequences:
                    issues.append(f"{where}: unknown light sequence {action.get('sequence')!r}")

    for state in states:
        name = state.get("id")
        for field in ("on_entry", "on_exit"):
            check_actions(state.get(field) or [], f"states.{name}.{field}")

    for index, transition in enumerate(payload.get("transitions") or []):
        where = f"transitions[{index}]"
        if transition.get("source") not in state_ids:
            issues.append(f"{where}: unknown source state {transition.get('source')!r}")
        if not transition.get("internal") and transition.get("target") not in state_ids:
            issues.append(f"{where}: unknown target state {transition.get('target')!r}")
        if not transition.get("trigger"):
            issues.append(f"{where}: trigger must not be empty")
        check_actions(transition.get("actions") or [], f"{where}.actions")

    for name, clip_set in clip_sets.items():
        for clip in clip_set.get("clips") or []:
            check_clip(clip, f"clip_sets.{name}")
    for name, effect in effects.items():
        for clip in effect.get("clips") or []:
            check_clip(clip, f"audio_effects.{name}")
    return issues
