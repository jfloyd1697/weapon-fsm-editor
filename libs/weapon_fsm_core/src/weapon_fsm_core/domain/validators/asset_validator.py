from pathlib import Path

from weapon_fsm_lights import validate_light_sequence

from weapon_fsm_core.domain.model import GunConfig, WeaponConfig
from weapon_fsm_core.domain.validation_context import ValidationContext
from weapon_fsm_core.domain.validation_types import ValidationIssue


class AssetValidator:
    def validate(
        self,
        *,
        gun: GunConfig,
        weapon: WeaponConfig,
        context: ValidationContext,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_clips(weapon))
        issues.extend(self._validate_clip_sets(weapon, context))
        issues.extend(self._validate_audio_effects(weapon, context))
        issues.extend(self._validate_light_sequences(weapon))
        return issues

    def _validate_clips(self, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for name, clip in weapon.clips.items():
            if not clip.path:
                issues.append(ValidationIssue(f"clips.{name}.path", "Clip path is required"))
                continue

            if weapon.source_path is not None:
                resolved = Path(weapon.resolve_asset_path(clip.path))
                if not resolved.exists():
                    issues.append(ValidationIssue(f"clips.{name}.path", f"Clip '{name}' points to missing file '{resolved}'"))

        return issues

    def _validate_clip_sets(self, weapon: WeaponConfig, context: ValidationContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for name, clip_set in weapon.clip_sets.items():
            if not clip_set.clips:
                issues.append(ValidationIssue(f"clip_sets.{name}.clips", "Clip set must include at least one clip"))
                continue

            missing = [clip_name for clip_name in clip_set.clips if clip_name not in context.clips]
            if missing:
                quoted = ", ".join(repr(item) for item in missing)
                issues.append(ValidationIssue(f"clip_sets.{name}.clips", f"Clip set '{name}' references unknown clip(s): {quoted}"))

        return issues

    def _validate_audio_effects(self, weapon: WeaponConfig, context: ValidationContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for name, effect in weapon.audio_effects.items():
            if not effect.clips:
                issues.append(ValidationIssue(f"audio_effects.{name}.clips", "Audio effect must include at least one clip"))
                continue

            missing = [clip_name for clip_name in effect.clips if clip_name not in context.clips]
            if missing:
                quoted = ", ".join(repr(item) for item in missing)
                issues.append(ValidationIssue(f"audio_effects.{name}.clips", f"Audio effect '{name}' references unknown clip(s): {quoted}"))

        return issues

    def _validate_light_sequences(self, weapon: WeaponConfig) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for name, sequence in weapon.light_sequences.items():
            if not sequence.path:
                issues.append(ValidationIssue(f"light_sequences.{name}.path", "Light sequence path is required"))
                continue

            if weapon.source_path is None:
                continue

            resolved = Path(weapon.resolve_asset_path(sequence.path))
            if not resolved.exists():
                issues.append(ValidationIssue(f"light_sequences.{name}.path", f"Light sequence '{name}' points to missing file '{sequence.path}'"))
                continue

            for error in validate_light_sequence(resolved):
                issues.append(ValidationIssue(f"light_sequences.{name}.path", f"Invalid light sequence '{name}': {error}"))

        return issues
