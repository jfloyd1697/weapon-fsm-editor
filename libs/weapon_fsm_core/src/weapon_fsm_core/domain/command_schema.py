from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationContext:
    states: set[str]
    variables: set[str]
    events: set[str]
    clips: set[str]
    clip_sets: set[str]
    light_sequences: set[str]
    audio_effects: set[str] | None = None


@dataclass(frozen=True)
class CommandFieldSpec:
    name: str
    required: bool = False
    expected_types: tuple[type, ...] = ()
    enum_values: tuple[object, ...] | None = None
    reference_target: str | None = None

    def validate(self, value: object, context: ValidationContext | None = None) -> list[str]:
        errors: list[str] = []
        if self.expected_types and not isinstance(value, self.expected_types):
            type_names = ", ".join(t.__name__ for t in self.expected_types)
            errors.append(f"'{self.name}' must be of type {type_names}")
            return errors
        if self.enum_values is not None and value not in self.enum_values:
            choices = ", ".join(repr(item) for item in self.enum_values)
            errors.append(f"'{self.name}' must be one of {choices}")
        if self.reference_target is not None and context is not None:
            target_values = getattr(context, self.reference_target, None)
            if target_values is not None and value not in target_values:
                singular = self.reference_target[:-1] if self.reference_target.endswith("s") else self.reference_target
                errors.append(f"Unknown {singular} '{value}'")
        return errors
