from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationContext:
    states: set[str]
    variables: set[str]
    events: set[str]
    clips: set[str]
    clip_sets: set[str]
    light_sequences: set[str]


@dataclass(frozen=True)
class SchemaValidationIssue:
    message: str


@dataclass(frozen=True)
class CommandFieldSpec:
    name: str
    required: bool = False
    expected_types: tuple[type, ...] = ()
    enum_values: tuple[object, ...] = ()
    reference_target: str | None = None

    def validate(self, value: Any, context: ValidationContext | None = None) -> list[str]:
        issues: list[str] = []

        if self.expected_types and not isinstance(value, self.expected_types):
            expected = ", ".join(t.__name__ for t in self.expected_types)
            issues.append(
                f"Field '{self.name}' must be of type {expected}, got {type(value).__name__}"
            )
            return issues

        if self.enum_values and value not in self.enum_values:
            allowed = ", ".join(repr(item) for item in self.enum_values)
            issues.append(
                f"Field '{self.name}' must be one of {allowed}, got {value!r}"
            )

        if self.reference_target and context is not None:
            pool = getattr(context, self.reference_target, None)
            if pool is None:
                issues.append(
                    f"Unknown validation reference target '{self.reference_target}'"
                )
            elif value not in pool:
                target_name = self.reference_target[:-1] if self.reference_target.endswith("s") else self.reference_target
                issues.append(f"Unknown {target_name} '{value}'")

        return issues
