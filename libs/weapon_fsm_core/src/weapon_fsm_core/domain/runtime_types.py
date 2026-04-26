from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduledEvent:
    event_id: str
    delay_ms: int


