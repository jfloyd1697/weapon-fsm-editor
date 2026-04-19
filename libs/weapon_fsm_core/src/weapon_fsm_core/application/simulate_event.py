from dataclasses import dataclass, field

from weapon_fsm_core.domain.model import GunConfig, WeaponConfig
from weapon_fsm_core.domain.runtime import TransitionResult, WeaponRuntime


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
        queue: list[str] = [event_id]
        while queue:
            next_event = queue.pop(0)
            result = self.runtime.handle_event(next_event)
            records.append(DispatchRecord(machine_id="weapon", result=result))
            if result.accepted:
                queue.extend(result.emitted_events)
        return records

    def advance_time(self, elapsed_ms: int) -> list[DispatchRecord]:
        records: list[DispatchRecord] = []
        for event_id in self.runtime.consume_due_events(elapsed_ms):
            records.extend(self.dispatch_external_event(event_id))
        return records
