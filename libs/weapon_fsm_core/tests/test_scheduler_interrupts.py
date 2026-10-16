"""Correctness and performance contracts for the desktop FSM scheduler."""

from time import perf_counter

import pytest

from weapon_fsm_core.application.simulate_event import SimulationService
from weapon_fsm_core.domain.model import ActionDef, GunConfig, StateDef, TransitionDef, WeaponConfig


def action(kind: str, **arguments: object) -> ActionDef:
    return ActionDef(type=kind, arguments=arguments)


def simulation(*, interval_ms: int = 60) -> SimulationService:
    weapon = WeaponConfig(
        initial_state="idle",
        states={
            "idle": StateDef(id="idle"),
            "firing": StateDef(
                id="firing", on_exit=[action("cancel_scheduled_events", event="shot")]
            ),
        },
        transitions=[
            TransitionDef(
                id="press", source="idle", target="firing", trigger="press",
                actions=[action("schedule_event", event="shot", delay_ms=interval_ms)],
            ),
            TransitionDef(
                id="repeat", source="firing", target="firing", trigger="shot", internal=True,
                actions=[
                    action("add_var", name="shots", value=1),
                    action("schedule_event", event="shot", delay_ms=interval_ms),
                ],
            ),
            TransitionDef(id="release", source="firing", target="idle", trigger="release"),
            TransitionDef(id="reload", source="firing", target="idle", trigger="reload"),
        ],
        variables={"shots": 0},
    )
    return SimulationService(GunConfig(), weapon)


def test_batched_time_repeats_at_the_authored_cadence() -> None:
    sim = simulation()
    assert sim.dispatch_external_event("press")[0].result.accepted
    shots = sim.advance_time(625)
    assert len(shots) == 10
    assert all(item.result.event_id == "shot" and item.result.accepted for item in shots)
    assert sim.runtime.variables["shots"] == 10
    assert sim.runtime.time_until_next_event_ms() == 35


def test_timer_is_cancelled_on_release_or_reload() -> None:
    for interrupt in ("release", "reload"):
        sim = simulation()
        sim.dispatch_external_event("press")
        sim.advance_time(59)
        assert sim.dispatch_external_event(interrupt)[0].result.accepted
        assert sim.runtime.current_state == "idle"
        assert sim.runtime.time_until_next_event_ms() is None
        assert sim.advance_time(1000) == []
        assert sim.runtime.variables["shots"] == 0


def test_release_followed_by_immediate_repress_does_not_resume_old_timer() -> None:
    sim = simulation()
    sim.dispatch_external_event("press")
    sim.advance_time(50)
    sim.dispatch_external_event("release")
    sim.dispatch_external_event("press")
    assert sim.advance_time(10) == []
    assert len(sim.advance_time(50)) == 1
    assert sim.runtime.variables["shots"] == 1


def test_due_event_can_cancel_another_event_due_at_same_time() -> None:
    weapon = WeaponConfig(
        initial_state="active",
        states={"active": StateDef(id="active"), "idle": StateDef(id="idle")},
        transitions=[
            TransitionDef(
                id="cancel", source="active", trigger="stop", target="idle",
                actions=[action("cancel_scheduled_events", event="shot")],
            ),
            TransitionDef(
                id="shot", source="active", trigger="shot", target="active", internal=True,
                actions=[action("add_var", name="shots", value=1)],
            ),
        ],
        variables={"shots": 0},
    )
    sim = SimulationService(GunConfig(), weapon)
    from weapon_fsm_core.domain.runtime_types import ScheduledEvent
    sim.runtime.pending_events.extend([ScheduledEvent("stop", 20), ScheduledEvent("shot", 20)])
    results = sim.advance_time(20)
    assert [item.result.event_id for item in results] == ["stop"]
    assert sim.runtime.variables["shots"] == 0
    assert sim.runtime.time_until_next_event_ms() is None


def test_multiple_due_events_preserve_insertion_order() -> None:
    weapon = WeaponConfig(
        initial_state="active", states={"active": StateDef(id="active")},
        transitions=[
            TransitionDef(id="a", source="active", target="active", trigger="a", internal=True),
            TransitionDef(id="b", source="active", target="active", trigger="b", internal=True),
        ],
    )
    sim = SimulationService(GunConfig(), weapon)
    from weapon_fsm_core.domain.runtime_types import ScheduledEvent
    sim.runtime.pending_events.extend([ScheduledEvent("a", 2), ScheduledEvent("b", 2)])
    assert [result.result.event_id for result in sim.advance_time(2)] == ["a", "b"]


def test_timer_with_zero_delay_can_fire_without_advancing_time() -> None:
    sim = simulation(interval_ms=0)
    # The 0 ms self-loop is invalid for running forever within one tick.
    sim.dispatch_external_event("press")
    with pytest.raises(RuntimeError, match="unbounded event cycle"):
        sim.advance_time(0)


def test_negative_elapsed_time_is_rejected() -> None:
    sim = simulation()
    with pytest.raises(ValueError):
        sim.advance_time(-1)


def test_unhandled_event_does_not_mutate_scheduler() -> None:
    sim = simulation()
    sim.dispatch_external_event("press")
    expected = list(sim.runtime.pending_events)
    assert not sim.dispatch_external_event("unknown")[0].result.accepted
    assert sim.runtime.pending_events == expected


def test_1000_repeats_do_not_require_wall_clock_delays() -> None:
    sim = simulation()
    sim.dispatch_external_event("press")
    start = perf_counter()
    events = sim.advance_time(60_000)
    elapsed = perf_counter() - start
    assert len(events) == 1000
    assert sim.runtime.variables["shots"] == 1000
    # Generous CI threshold; this should take milliseconds, not the simulated 60 seconds.
    assert elapsed < 2.0


def test_reset_discards_pending_timers_and_runtime_variables() -> None:
    sim = simulation()
    sim.dispatch_external_event("press")
    sim.advance_time(60)
    assert sim.runtime.variables["shots"] == 1
    sim.reset()
    assert sim.runtime.current_state == "idle"
    assert sim.runtime.variables["shots"] == 0
    assert sim.runtime.pending_events == []
    assert sim.advance_time(2000) == []


def test_interleaved_input_interrupts_do_not_replay_old_callbacks() -> None:
    sim = simulation()
    for _ in range(100):
        sim.dispatch_external_event("press")
        sim.advance_time(30)
        sim.dispatch_external_event("release")
        sim.advance_time(30)
    assert sim.runtime.variables["shots"] == 0
    assert sim.runtime.pending_events == []
