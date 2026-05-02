from weapon_fsm_core.domain.commands import RuntimeCommand
from weapon_fsm_core.domain.model import ActionDef, GunConfig, WeaponConfig
from weapon_fsm_core.domain.validation_context import ValidationContext
from weapon_fsm_core.domain.validation_types import ValidationIssue


class ActionValidator:
    def validate(
        self,
        *,
        gun: GunConfig,
        weapon: WeaponConfig,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for state in weapon.states.values():
            issues.extend(self._validate_actions(actions=state.on_entry, path=f"weapon.states.{state.id}.on_entry", context=context))
            issues.extend(self._validate_actions(actions=state.on_exit, path=f"weapon.states.{state.id}.on_exit", context=context))

        for transition in weapon.transitions:
            issues.extend(self._validate_actions(actions=transition.actions, path=f"weapon.transitions.{transition.id}.actions", context=context))

        return issues

    def _validate_actions(
        self,
        *,
        actions: list[ActionDef],
        path: str,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for index, action in enumerate(actions):
            for message in RuntimeCommand.validate_action(action, context):
                issues.append(ValidationIssue(f"{path}.{index}", message))

        return issues
