from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import ActionDef, GuardDef, GunConfig, StateDef, TransitionDef, WeaponConfig
    from .runtime import RuntimeCommand, ScheduledEvent, TransitionResult, WeaponRuntime
    from .validation import ProfileValidator, ValidationIssue

__all__ = [
    "ActionDef",
    "GuardDef",
    "GunConfig",
    "StateDef",
    "TransitionDef",
    "WeaponConfig",
    "RuntimeCommand",
    "ScheduledEvent",
    "TransitionResult",
    "WeaponRuntime",
    "ProfileValidator",
    "ValidationIssue",
]


def __getattr__(name: str):
    if name in {
        "ActionDef",
        "GuardDef",
        "GunConfig",
        "StateDef",
        "TransitionDef",
        "WeaponConfig",
    }:
        from .model import ActionDef, GuardDef, GunConfig, StateDef, TransitionDef, WeaponConfig

        return {
            "ActionDef": ActionDef,
            "GuardDef": GuardDef,
            "GunConfig": GunConfig,
            "StateDef": StateDef,
            "TransitionDef": TransitionDef,
            "WeaponConfig": WeaponConfig,
        }[name]

    if name in {"RuntimeCommand", "ScheduledEvent", "TransitionResult", "WeaponRuntime"}:
        from .runtime import RuntimeCommand, ScheduledEvent, TransitionResult, WeaponRuntime

        return {
            "RuntimeCommand": RuntimeCommand,
            "ScheduledEvent": ScheduledEvent,
            "TransitionResult": TransitionResult,
            "WeaponRuntime": WeaponRuntime,
        }[name]

    if name in {"ProfileValidator", "ValidationIssue"}:
        from .validation import ProfileValidator, ValidationIssue

        return {
            "ProfileValidator": ProfileValidator,
            "ValidationIssue": ValidationIssue,
        }[name]
    raise AttributeError(name)
