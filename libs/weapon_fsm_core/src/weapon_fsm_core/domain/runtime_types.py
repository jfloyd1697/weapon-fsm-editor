from dataclasses import dataclass, field

from .model import TransitionDef


@dataclass(frozen=True)
class ScheduledEvent:
    event_id: str
    delay_ms: int


@dataclass(frozen=True)
class TransitionResult:
    accepted: bool
    event_id: str
    previous_state: str
    current_state: str
    transition: TransitionDef | None = None
    emitted_events: tuple[str, ...] = ()
    scheduled_events: tuple[ScheduledEvent, ...] = ()
    commands: tuple[object, ...] = ()
    variables_before: dict[str, object] = field(default_factory=dict)
    variables_after: dict[str, object] = field(default_factory=dict)
    reason: str | None = None
