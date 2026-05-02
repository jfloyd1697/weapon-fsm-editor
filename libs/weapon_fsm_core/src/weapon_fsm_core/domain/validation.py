from dataclasses import dataclass, field
from typing import Protocol

from .model import GunConfig, WeaponConfig
from .validation_context import ValidationContext
from .validation_types import ValidationIssue
from .validators import ActionValidator, AssetValidator, GuardValidator, StructureValidator


class ProfileValidationRule(Protocol):
    def validate(
        self,
        *,
        gun: GunConfig,
        weapon: WeaponConfig,
        context: ValidationContext,
    ) -> list[ValidationIssue]: ...


@dataclass
class ProfileValidator:
    rules: list[ProfileValidationRule] = field(
        default_factory=lambda: [
            StructureValidator(),
            GuardValidator(),
            AssetValidator(),
            ActionValidator(),
        ]
    )

    def validate(self, gun: GunConfig, weapon: WeaponConfig) -> list[ValidationIssue]:
        context = ValidationContext.from_profile(gun, weapon)
        issues: list[ValidationIssue] = []

        for rule in self.rules:
            issues.extend(rule.validate(gun=gun, weapon=weapon, context=context))

        return issues
