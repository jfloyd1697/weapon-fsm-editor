from collections import deque
from dataclasses import dataclass, field

from weapon_fsm_core.domain.model import GunConfig, WeaponConfig
from weapon_fsm_core.domain.runtime import WeaponRuntime
from weapon_fsm_core.domain import TransitionResult


@dataclass(frozen=True)
class DispatchRecord:
    machine_id: str
    result: TransitionResult


@dataclass
class SimulationService:
    gun: GunConfig
    weapon: WeaponConfig
    runtime: WeaponRuntime = field(init=False)

    def __post_init__(self) -> None:
        self.runtime = WeaponRuntime(self.gun, self.weapon)

    @property
    def gun_runtime(self) -> WeaponRuntime:
        return self.runtime

    @property
    def behavior_runtime(self) -> WeaponRuntime:
        return self.runtime

    def reset(self) -> None:
        self.runtime.reset()

    def dispatch_external_event(self, event_id: str) -> list[DispatchRecord]:
        records: list[DispatchRecord] = []
        queue = deque([event_id])
        while queue:
            next_event = queue.popleft()
            result = self.runtime.handle_event(next_event)
            records.append(DispatchRecord(machine_id="weapon", result=result))
            if result.accepted:
                queue.extend(result.emitted_events)
        return records

    def advance_time(self, elapsed_ms: int) -> list[DispatchRecord]:
        """Advance timers chronologically, including events scheduled by due events.

        An interrupt at a deadline can cancel another event at that deadline.
        Unlike a fixed-step timer, an arbitrarily long elapsed interval retains
        the authored event cadence rather than delaying each repeat to the next tick.
        """
        if elapsed_ms < 0:
            raise ValueError("Elapsed time cannot be negative")

        records: list[DispatchRecord] = []
        remaining_ms = elapsed_ms
        processed = 0
        max_events = 10000  # A malformed zero-delay cycle must not lock the GUI.
        while (delay := self.runtime.time_until_next_event_ms()) is not None:
            if delay > remaining_ms:
                break
            step = max(0, delay)
            self.runtime.elapse_pending_events(step)
            remaining_ms -= step

            event_id = self.runtime.pop_next_due_event()
            if event_id is None:
                break
            processed += 1
            if processed > max_events:
                raise RuntimeError("Simulation scheduled an unbounded event cycle")
            records.extend(self.dispatch_external_event(event_id))

        self.runtime.elapse_pending_events(remaining_ms)
        return records
