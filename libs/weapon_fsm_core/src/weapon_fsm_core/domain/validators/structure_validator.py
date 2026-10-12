from weapon_fsm_core.domain.model import GunConfig, WeaponConfig
from weapon_fsm_core.domain.validation_context import ValidationContext
from weapon_fsm_core.domain.validation_types import ValidationIssue


class StructureValidator:
    def validate(
        self,
        *,
        gun: GunConfig,
        weapon: WeaponConfig,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if weapon.initial_state not in context.states:
            issues.append(
                ValidationIssue(
                    "weapon.initial_state",
                    f"Unknown initial state '{weapon.initial_state}'",
                )
            )

        for transition in weapon.transitions:
            path = f"weapon.transitions.{transition.id}"

            if transition.source not in context.states:
                issues.append(ValidationIssue(f"{path}.source", f"Unknown source state '{transition.source}'"))

            if transition.target not in context.states:
                issues.append(ValidationIssue(f"{path}.target", f"Unknown target state '{transition.target}'"))

            if transition.trigger not in context.events:
                issues.append(ValidationIssue(f"{path}.trigger", f"Unknown trigger '{transition.trigger}'"))

        return issues
