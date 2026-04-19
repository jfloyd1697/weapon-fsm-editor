import traceback
from dataclasses import dataclass, field
import random

from .model import ActionDef, GunConfig, GuardDef, TransitionDef, WeaponConfig


@dataclass(frozen=True)
class ScheduledEvent:
    event_id: str
    delay_ms: int


@dataclass(frozen=True)
class RuntimeCommand:
    type: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TransitionResult:
    accepted: bool
    event_id: str
    previous_state: str
    current_state: str
    transition: TransitionDef | None = None
    emitted_events: tuple[str, ...] = ()
    scheduled_events: tuple[ScheduledEvent, ...] = ()
    commands: tuple[RuntimeCommand, ...] = ()
    variables_before: dict[str, object] = field(default_factory=dict)
    variables_after: dict[str, object] = field(default_factory=dict)
    reason: str | None = None


@dataclass
class WeaponRuntime:
    gun: GunConfig
    weapon: WeaponConfig
    current_state: str = field(init=False)
    variables: dict[str, object] = field(init=False)
    trigger_pressed: bool = field(init=False)
    last_transition_id: str | None = field(default=None, init=False)
    pending_events: list[ScheduledEvent] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.current_state = self.weapon.initial_state
        self.variables = dict(self.weapon.variables)
        self.trigger_pressed = False
        self.variables["trigger_down"] = False
        self.last_transition_id = None
        self.pending_events = []
        self._run_actions(self.weapon.states[self.current_state].on_entry)

    def valid_transitions(self) -> tuple[TransitionDef, ...]:
        return tuple(
            transition
            for transition in self.weapon.transitions_from(self.current_state)
            if self._guard_allows(transition.guard)
        )

    def handle_event(self, event_id: str) -> TransitionResult:
        previous_state = self.current_state
        variables_before = dict(self.variables)

        if event_id == "trigger_pressed":
            self.trigger_pressed = True
            self.variables["trigger_down"] = True
        elif event_id == "trigger_released":
            self.trigger_pressed = False
            self.variables["trigger_down"] = False

        try:
            for transition in self.weapon.transitions_from(self.current_state):
                if transition.trigger != event_id:
                    continue
                if not self._guard_allows(transition.guard):
                    continue

                current_state_def = self.weapon.states[self.current_state]
                emitted_events, scheduled_events, commands = self._run_actions(
                    current_state_def.on_exit
                )

                transition_emits, transition_scheduled, transition_commands = self._run_actions(
                    transition.actions
                )
                emitted_events.extend(transition_emits)
                scheduled_events.extend(transition_scheduled)
                commands.extend(transition_commands)

                self.current_state = transition.target
                self.last_transition_id = transition.id

                target_state_def = self.weapon.states[self.current_state]
                entry_emits, entry_scheduled, entry_commands = self._run_actions(
                    target_state_def.on_entry
                )
                emitted_events.extend(entry_emits)
                scheduled_events.extend(entry_scheduled)
                commands.extend(entry_commands)

                self.pending_events.extend(scheduled_events)

                return TransitionResult(
                    accepted=True,
                    event_id=event_id,
                    previous_state=previous_state,
                    current_state=self.current_state,
                    transition=transition,
                    emitted_events=tuple(emitted_events),
                    scheduled_events=tuple(scheduled_events),
                    commands=tuple(commands),
                    variables_before=variables_before,
                    variables_after=dict(self.variables),
                )
        except Exception:
            return TransitionResult(
                accepted=False,
                event_id=event_id,
                previous_state=previous_state,
                current_state=self.current_state,
                variables_before=variables_before,
                variables_after=dict(self.variables),
                reason=f"Error during transition: {traceback.format_exc()}",
            )

        return TransitionResult(
            accepted=False,
            event_id=event_id,
            previous_state=previous_state,
            current_state=self.current_state,
            variables_before=variables_before,
            variables_after=dict(self.variables),
            reason=f"No transition for event '{event_id}' from state '{self.current_state}'",
        )

    def consume_due_events(self, elapsed_ms: int) -> list[str]:
        ready: list[str] = []
        remaining: list[ScheduledEvent] = []

        for pending in self.pending_events:
            updated = ScheduledEvent(
                event_id=pending.event_id,
                delay_ms=pending.delay_ms - elapsed_ms,
            )
            if updated.delay_ms <= 0:
                ready.append(updated.event_id)
            else:
                remaining.append(updated)

        self.pending_events = remaining
        return ready

    def _guard_allows(self, guard: GuardDef | None) -> bool:
        if guard is None:
            return True
        return guard.evaluate(
            variables=self.variables,
            trigger_pressed=self.trigger_pressed,
        )

    def _run_actions(
        self,
        actions: tuple[ActionDef, ...],
    ) -> tuple[list[str], list[ScheduledEvent], list[RuntimeCommand]]:
        emitted: list[str] = []
        scheduled: list[ScheduledEvent] = []
        commands: list[RuntimeCommand] = []

        for action in actions:
            action_type = action.type

            if action_type == "play_audio":
                commands.append(RuntimeCommand("play_audio", dict(action.arguments)))

            elif action_type == "play_audio_loop":
                commands.append(RuntimeCommand("play_audio_loop", dict(action.arguments)))

            elif action_type == "play_random_audio":
                payload = dict(action.arguments)
                clips = payload.get("clips", [])
                if isinstance(clips, list) and clips:
                    payload["clip"] = random.choice(clips)
                commands.append(RuntimeCommand("play_random_audio", payload))

            elif action_type == "stop_audio":
                commands.append(RuntimeCommand("stop_audio", dict(action.arguments)))

            elif action_type == "start_light_sequence":
                commands.append(RuntimeCommand("start_light_sequence", dict(action.arguments)))

            elif action_type == "stop_light_sequence":
                commands.append(RuntimeCommand("stop_light_sequence", dict(action.arguments)))

            elif action_type == "set_var":
                name = str(action.argument("name"))
                if "value_from_var" in action.arguments:
                    source_name = str(action.argument("value_from_var"))
                    self.variables[name] = self.variables.get(source_name)
                else:
                    self.variables[name] = action.argument("value")

            elif action_type == "add_var":
                name = str(action.argument("name"))
                delta = action.argument("value", 0)
                current = self.variables.get(name, 0)
                self.variables[name] = current + delta

            elif action_type == "adjust_ammo":
                delta = int(action.argument("delta", 0))
                ammo = int(self.variables.get("ammo", 0))
                mag_capacity = int(self.variables.get("mag_capacity", ammo))
                self.variables["ammo"] = max(0, min(mag_capacity, ammo + delta))

            elif action_type == "set_ammo":
                value = int(action.argument("value", self.variables.get("ammo", 0)))
                mag_capacity = int(self.variables.get("mag_capacity", value))
                self.variables["ammo"] = max(0, min(mag_capacity, value))

            elif action_type == "set_ammo_full":
                mag_capacity = int(self.variables.get("mag_capacity", 0))
                self.variables["ammo"] = mag_capacity

            elif action_type == "emit_event":
                event_id = action.argument("event")
                if event_id:
                    emitted.append(str(event_id))

            elif action_type == "schedule_event":
                event_id = action.argument("event")
                delay_ms = int(action.argument("delay_ms", 0))
                if event_id:
                    scheduled.append(ScheduledEvent(str(event_id), delay_ms))

            elif action_type == "chance_event":
                chance = float(action.argument("chance", 0.0))
                event_id = action.argument("event")
                if event_id and random.random() <= chance:
                    emitted.append(str(event_id))

            elif action_type == "log":
                commands.append(RuntimeCommand("log", dict(action.arguments)))

            else:
                commands.append(RuntimeCommand(action_type, dict(action.arguments)))

        return emitted, scheduled, commands