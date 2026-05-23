from typing import Any

from weapon_fsm_core.domain.model import GuardDef, GunConfig, WeaponConfig
from weapon_fsm_core.domain.validation_context import ValidationContext
from weapon_fsm_core.domain.validation_types import ValidationIssue


class GuardValidator:
    def validate(
        self,
        *,
        gun: GunConfig,
        weapon: WeaponConfig,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for transition in weapon.transitions:
            if transition.guard is not None:
                issues.extend(
                    self._validate_guard(
                        guard=transition.guard,
                        path=f"weapon.transitions.{transition.id}.guard",
                        context=context,
                    )
                )

        return issues

    def _validate_guard(
        self,
        *,
        guard: GuardDef,
        path: str,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for name, spec in (
            ("var_eq", guard.var_eq),
            ("var_gt", guard.var_gt),
            ("var_gte", guard.var_gte),
            ("var_lt", guard.var_lt),
            ("var_lte", guard.var_lte),
        ):
            if spec is not None:
                issues.extend(self._validate_compare(spec=spec, path=f"{path}.{name}", context=context))

        for index, child in enumerate(guard.all):
            issues.extend(self._validate_guard(guard=child, path=f"{path}.all.{index}", context=context))

        for index, child in enumerate(guard.any):
            issues.extend(self._validate_guard(guard=child, path=f"{path}.any.{index}", context=context))

        return issues

    def _validate_compare(
        self,
        *,
        spec: dict[str, Any],
        path: str,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        name = spec.get("name")
        if not name:
            return [ValidationIssue(path, "Missing variable name")]

        variable_name = str(name)
        if variable_name not in context.variables:
            issues.append(ValidationIssue(f"{path}.name", f"Unknown variable '{variable_name}'"))

        has_value = "value" in spec
        has_value_from_var = "value_from_var" in spec

        if not has_value and not has_value_from_var:
            issues.append(ValidationIssue(path, "Guard compare must specify either 'value' or 'value_from_var'"))

        if has_value and has_value_from_var:
            issues.append(ValidationIssue(path, "Guard compare cannot specify both 'value' and 'value_from_var'"))

        if has_value_from_var:
            other_name = str(spec["value_from_var"])
            if other_name not in context.variables:
                issues.append(ValidationIssue(f"{path}.value_from_var", f"Unknown variable '{other_name}'"))

        return issues
