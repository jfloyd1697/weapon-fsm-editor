import traceback
from dataclasses import dataclass, field

from .commands import RuntimeCommand, RuntimeEnvironment, GunRuntimeCommand
from .model import ActionDef, GunConfig, GuardDef, TransitionDef, WeaponConfig
from .runtime_types import ScheduledEvent, TransitionResult


@dataclass
class WeaponRuntime:
    gun: GunConfig
    weapon: WeaponConfig
    current_state: str = field(init=False)
    variables: dict[str, object] = field(init=False)
    trigger_pressed: bool = field(init=False)
    last_transition_id: str | None = field(default=None, init=False)
    pending_events: list[ScheduledEvent] = field(default_factory=list, init=False)
    clip_set_state: dict[str, dict[str, int | str | tuple[int, ...]]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.current_state = self.weapon.initial_state
        self.variables = dict(self.weapon.variables)
        self.trigger_pressed = False
        self.variables["trigger_down"] = False
        self.last_transition_id = None
        self.pending_events = []
        self.clip_set_state = {}
        self._run_actions(self.weapon.states[self.current_state].on_entry)

    def valid_transitions(self) -> tuple[TransitionDef, ...]:
        return tuple(
            transition
            for transition in self.weapon.transitions_from(self.current_state)
            if self._guard_allows(transition.guard)
        )

    def handle_event(self, event_id: str) -> TransitionResult:
        previous_state = self.current_state
        state_at_start = self.current_state
        variables_before = dict(self.variables)
        pending_before = list(self.pending_events)
        last_transition_before = self.last_transition_id
        trigger_pressed_before = self.trigger_pressed

        try:
            if event_id == "trigger_pressed":
                self.trigger_pressed = True
                self.variables["trigger_down"] = True
            elif event_id == "trigger_released":
                self.trigger_pressed = False
                self.variables["trigger_down"] = False

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
            self.current_state = state_at_start
            self.variables = dict(variables_before)
            self.pending_events = pending_before
            self.last_transition_id = last_transition_before
            self.trigger_pressed = trigger_pressed_before

            return TransitionResult(
                accepted=False,
                event_id=event_id,
                previous_state=previous_state,
                current_state=self.current_state,
                variables_before=variables_before,
                variables_after=dict(self.variables),
                reason=(
                    f"Error processing event '{event_id}' from state "
                    f"'{state_at_start}': {traceback.format_exc()}"
                ),
            )
        else:
            return TransitionResult(
                accepted=False,
                event_id=event_id,
                previous_state=previous_state,
                current_state=self.current_state,
                variables_before=variables_before,
                variables_after=dict(self.variables),
                reason=f"No transition for event '{event_id}' from state '{state_at_start}'",
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
    ) -> tuple[list[str], list[ScheduledEvent], list[GunRuntimeCommand]]:
        env = RuntimeEnvironment(
            weapon=self.weapon,
            variables=self.variables,
            clip_set_state=self.clip_set_state,
        )

        for action in actions:
            command = RuntimeCommand.from_action(action)
            command.execute(env)

        return env.emitted_events, env.scheduled_events, env.gun_commands