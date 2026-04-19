from dataclasses import dataclass

from .model import ActionDef, GunConfig, WeaponConfig


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


class ProfileValidator:
    def validate(self, gun: GunConfig, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_weapon(weapon))
        issues.extend(self._validate_triggers(gun, weapon))
        issues.extend(self._validate_actions(gun, weapon))
        return issues

    def _validate_weapon(self, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if weapon.initial_state not in weapon.states:
            issues.append(ValidationIssue("weapon.initial_state", f"Unknown initial state '{weapon.initial_state}'"))

        for transition in weapon.transitions:
            if transition.source not in weapon.states:
                issues.append(ValidationIssue(f"weapon.transitions.{transition.id}.source", f"Unknown source state '{transition.source}'"))
            if transition.target not in weapon.states:
                issues.append(ValidationIssue(f"weapon.transitions.{transition.id}.target", f"Unknown target state '{transition.target}'"))
        return issues

    def _validate_triggers(self, gun: GunConfig, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        available_events = set(gun.events)
        available_events.update(self._events_from_actions(weapon))

        for transition in weapon.transitions:
            if transition.trigger not in available_events:
                issues.append(ValidationIssue(
                    f"weapon.transitions.{transition.id}.trigger",
                    f"Unknown trigger '{transition.trigger}'",
                ))
        return issues

    def _validate_actions(self, gun: GunConfig, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        available_events = set(gun.events)
        available_events.update(self._events_from_actions(weapon))

        for state in weapon.states.values():
            for idx, action in enumerate(state.on_entry):
                issues.extend(self._validate_action(action, f"weapon.states.{state.id}.on_entry.{idx}", available_events))
            for idx, action in enumerate(state.on_exit):
                issues.extend(self._validate_action(action, f"weapon.states.{state.id}.on_exit.{idx}", available_events))
        for transition in weapon.transitions:
            for idx, action in enumerate(transition.actions):
                issues.extend(self._validate_action(action, f"weapon.transitions.{transition.id}.actions.{idx}", available_events))
        return issues

    def _validate_action(self, action: ActionDef, path: str, available_events: set[str]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if action.type in {"emit_event", "schedule_event"}:
            event_id = action.argument("event")
            if not event_id:
                issues.append(ValidationIssue(path, "Missing event for event action"))
            elif event_id not in available_events:
                issues.append(ValidationIssue(path, f"Unknown event '{event_id}'"))
        if action.type in {"play_audio", "play_audio_loop", "play_random_audio", "play_sound", "play_sound_loop", "play_random_sound"}:
            interrupt = action.argument("interrupt", "interrupt")
            if interrupt not in {"interrupt", "schedule", "ignore"}:
                issues.append(ValidationIssue(path, f"Unknown interrupt behavior '{interrupt}'"))
        return issues

    def _events_from_actions(self, weapon: WeaponConfig) -> set[str]:
        discovered: set[str] = set()
        for state in weapon.states.values():
            for action in state.on_entry + state.on_exit:
                if action.type in {"emit_event", "schedule_event"}:
                    event_id = action.argument("event")
                    if event_id:
                        discovered.add(str(event_id))
        for transition in weapon.transitions:
            for action in transition.actions:
                if action.type in {"emit_event", "schedule_event"}:
                    event_id = action.argument("event")
                    if event_id:
                        discovered.add(str(event_id))
        return discovered
