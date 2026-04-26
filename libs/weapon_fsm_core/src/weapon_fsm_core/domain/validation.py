from dataclasses import dataclass
from pathlib import Path

from weapon_fsm_lights import validate_light_sequence

from .command_schema import ValidationContext
from .commands import RuntimeCommand
from .model import ActionDef, GuardDef, GunConfig, WeaponConfig


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


class ProfileValidator:
    def validate(self, gun: GunConfig, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        context = self._build_context(gun, weapon)

        issues.extend(self._validate_weapon(weapon))
        issues.extend(self._validate_triggers(gun, weapon))
        issues.extend(self._validate_guards(weapon, context))
        issues.extend(self._validate_assets(weapon))
        issues.extend(self._validate_actions(weapon, context))
        return issues

    def _build_context(self, gun: GunConfig, weapon: WeaponConfig) -> ValidationContext:
        events = set(gun.events)
        events.update(self._events_from_actions(weapon))
        variables = set(weapon.variables.keys())
        variables.add("trigger_down")
        states = set(state.id for state in weapon.states)
        clips = set(weapon.clips.keys())
        clip_sets = set(weapon.clip_sets.keys())
        light_sequences = set(weapon.light_sequences.keys())
        # audio_effects = set(weapon.audio_effects.keys())
        audio_effects = set()
        return ValidationContext(
            states=states,
            variables=variables,
            events=events,
            clips=clips,
            clip_sets=clip_sets,
            light_sequences=light_sequences,
            audio_effects=audio_effects,
        )

    def _validate_weapon(self, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if weapon.initial_state not in weapon.states:
            issues.append(
                ValidationIssue(
                    "weapon.initial_state",
                    f"Unknown initial state '{weapon.initial_state}'",
                )
            )

        for transition in weapon.transitions:
            if transition.source not in weapon.states:
                issues.append(
                    ValidationIssue(
                        f"weapon.transitions.{transition.id}.source",
                        f"Unknown source state '{transition.source}'",
                    )
                )
            if transition.target not in weapon.states:
                issues.append(
                    ValidationIssue(
                        f"weapon.transitions.{transition.id}.target",
                        f"Unknown target state '{transition.target}'",
                    )
                )

        return issues

    def _validate_triggers(self, gun: GunConfig, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        available_events = set(gun.events)
        available_events.update(self._events_from_actions(weapon))

        for transition in weapon.transitions:
            if transition.trigger not in available_events:
                issues.append(
                    ValidationIssue(
                        f"weapon.transitions.{transition.id}.trigger",
                        f"Unknown trigger '{transition.trigger}'",
                    )
                )

        return issues

    def _validate_assets(self, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for name, clip in weapon.clips.items():
            if not clip.path:
                issues.append(ValidationIssue(f"clips.{name}.path", "Clip path is required"))
                continue
            if weapon.source_path is not None:
                resolved = Path(weapon.resolve_asset_path(clip.path))
                if not resolved.exists():
                    issues.append(
                        ValidationIssue(
                            f"clips.{name}.path",
                            f"Clip '{name}' points to missing file '{clip.path}'",
                        )
                    )

        for name, clip_set in weapon.clip_sets.items():
            if not clip_set.clips:
                issues.append(ValidationIssue(f"clip_sets.{name}.clips", "Clip set must include at least one clip"))
                continue
            missing = [clip_name for clip_name in clip_set.clips if clip_name not in weapon.clips]
            if missing:
                quoted = ", ".join(repr(item) for item in missing)
                issues.append(
                    ValidationIssue(
                        f"clip_sets.{name}.clips",
                        f"Clip set '{name}' references unknown clip(s): {quoted}",
                    )
                )
            if clip_set.mode not in {"random", "random_no_repeat", "sequence"}:
                issues.append(
                    ValidationIssue(
                        f"clip_sets.{name}.mode",
                        f"Clip set '{name}' has invalid mode '{clip_set.mode}'",
                    )
                )

        for name, effect in getattr(weapon, "audio_effects", {}).items():
            if not effect.clips:
                issues.append(
                    ValidationIssue(
                        f"audio.effects.{name}.clips",
                        f"Audio effect '{name}' must reference at least one clip",
                    )
                )
                continue

            missing = [clip_name for clip_name in effect.clips if clip_name not in weapon.clips]
            if missing:
                quoted = ", ".join(repr(item) for item in missing)
                issues.append(
                    ValidationIssue(
                        f"audio.effects.{name}.clips",
                        f"Audio effect '{name}' references unknown clip(s): {quoted}",
                    )
                )

            if effect.resolved_mode not in {"one_shot", "loop", "random"}:
                issues.append(
                    ValidationIssue(
                        f"audio.effects.{name}.mode",
                        f"Audio effect '{name}' has invalid mode '{effect.mode}'",
                    )
                )

            if effect.interrupt not in {"interrupt", "schedule", "ignore"}:
                issues.append(
                    ValidationIssue(
                        f"audio.effects.{name}.interrupt",
                        f"Audio effect '{name}' has invalid interrupt '{effect.interrupt}'",
                    )
                )

        for name, sequence in weapon.light_sequences.items():
            if not sequence.path:
                issues.append(ValidationIssue(f"light_sequences.{name}.path", "Light sequence path is required"))
                continue
            if weapon.source_path is not None:
                resolved = Path(weapon.resolve_asset_path(sequence.path))
                if not resolved.exists():
                    issues.append(
                        ValidationIssue(
                            f"light_sequences.{name}.path",
                            f"Light sequence '{name}' points to missing file '{sequence.path}'",
                        )
                    )
                    continue
                for error in validate_light_sequence(resolved):
                    issues.append(
                        ValidationIssue(
                            f"light_sequences.{name}.path",
                            f"Invalid light sequence '{name}': {error}",
                        )
                    )
        return issues

    def _validate_guards(
        self,
        weapon: WeaponConfig,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for transition in weapon.transitions:
            issues.extend(
                self._validate_guard(
                    transition.guard,
                    f"weapon.transitions.{transition.id}.guard",
                    context,
                )
            )
        return issues

    def _validate_guard(
        self,
        guard: GuardDef | None,
        path: str,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if guard is None:
            return issues

        for name, spec in (
            ("var_eq", guard.var_eq),
            ("var_gt", guard.var_gt),
            ("var_gte", guard.var_gte),
            ("var_lt", guard.var_lt),
            ("var_lte", guard.var_lte),
        ):
            if spec is not None:
                issues.extend(
                    self._validate_guard_compare(
                        spec,
                        f"{path}.{name}",
                        context,
                    )
                )

        for index, child in enumerate(guard.all):
            issues.extend(self._validate_guard(child, f"{path}.all.{index}", context))

        for index, child in enumerate(guard.any):
            issues.extend(self._validate_guard(child, f"{path}.any.{index}", context))

        return issues

    def _validate_guard_compare(
        self,
        spec: dict[str, object],
        path: str,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        name = spec.get("name")
        if not name:
            issues.append(ValidationIssue(path, "Missing variable name"))
            return issues

        variable_name = str(name)
        if variable_name not in context.variables:
            issues.append(
                ValidationIssue(
                    f"{path}.name",
                    f"Unknown variable '{variable_name}'",
                )
            )

        has_value = "value" in spec
        has_value_from_var = "value_from_var" in spec

        if not has_value and not has_value_from_var:
            issues.append(
                ValidationIssue(
                    path,
                    "Guard compare must specify either 'value' or 'value_from_var'",
                )
            )

        if has_value and has_value_from_var:
            issues.append(
                ValidationIssue(
                    path,
                    "Guard compare cannot specify both 'value' and 'value_from_var'",
                )
            )

        if has_value_from_var:
            other_name = str(spec["value_from_var"])
            if other_name not in context.variables:
                issues.append(
                    ValidationIssue(
                        f"{path}.value_from_var",
                        f"Unknown variable '{other_name}'",
                    )
                )

        return issues

    def _validate_actions(
        self,
        weapon: WeaponConfig,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for state in weapon.states:
            for index, action in enumerate(state.on_entry):
                issues.extend(
                    self._validate_action(
                        action,
                        f"weapon.states.{state.id}.on_entry.{index}",
                        context,
                    )
                )
            for index, action in enumerate(state.on_exit):
                issues.extend(
                    self._validate_action(
                        action,
                        f"weapon.states.{state.id}.on_exit.{index}",
                        context,
                    )
                )

        for transition in weapon.transitions:
            for index, action in enumerate(transition.actions):
                issues.extend(
                    self._validate_action(
                        action,
                        f"weapon.transitions.{transition.id}.actions.{index}",
                        context,
                    )
                )

        return issues

    def _validate_action(
        self,
        action: ActionDef,
        path: str,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        return [
            ValidationIssue(path, message)
            for message in RuntimeCommand.validate_action(action, context)
        ]

    def _events_from_actions(self, weapon: WeaponConfig) -> set[str]:
        discovered: set[str] = set()

        for state in weapon.states:
            for action in state.on_entry + state.on_exit:
                if action.type in {"emit_event", "schedule_event", "chance_event"}:
                    event_id = action.argument("event")
                    if event_id:
                        discovered.add(str(event_id))

        for transition in weapon.transitions:
            for action in transition.actions:
                if action.type in {"emit_event", "schedule_event", "chance_event"}:
                    event_id = action.argument("event")
                    if event_id:
                        discovered.add(str(event_id))

        return discovered
