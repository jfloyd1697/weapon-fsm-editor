from __future__ import annotations

from dataclasses import dataclass

from .model import GunConfig, WeaponConfig


@dataclass(frozen=True)
class ValidationContext:
    states: set[str]
    variables: set[str]
    events: set[str]
    clips: set[str]
    clip_sets: set[str]
    light_sequences: set[str]
    audio_effects: set[str]

    @classmethod
    def from_profile(cls, gun: GunConfig, weapon: WeaponConfig) -> "ValidationContext":
        events = set(gun.events)
        events.update(events_from_actions(weapon))

        variables = set(weapon.variables.keys())
        variables.add("trigger_down")

        return cls(
            states=set(weapon.states.keys()),
            variables=variables,
            events=events,
            clips=set(weapon.clips.keys()),
            clip_sets=set(weapon.clip_sets.keys()),
            light_sequences=set(weapon.light_sequences.keys()),
            audio_effects=set(weapon.audio_effects.keys()),
        )


def events_from_actions(weapon: WeaponConfig) -> set[str]:
    discovered: set[str] = set()

    for state in weapon.states.values():
        _collect_events_from_actions(state.on_entry, discovered)
        _collect_events_from_actions(state.on_exit, discovered)

    for transition in weapon.transitions:
        _collect_events_from_actions(transition.actions, discovered)

    return discovered


def _collect_events_from_actions(actions, discovered: set[str]) -> None:
    for action in actions:
        if action.type in {"emit_event", "schedule_event", "chance_event"}:
            event_id = action.argument("event")
            if event_id:
                discovered.add(str(event_id))
