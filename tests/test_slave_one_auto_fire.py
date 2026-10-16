"""Regression for one-state timer-driven automatic fire."""

from __future__ import annotations

from pathlib import Path

import yaml

from weapon_fsm_core.application.simulate_event import SimulationService
from weapon_fsm_core.domain.model import ActionDef, GunConfig, StateDef, TransitionDef, WeaponConfig
from weapon_fsm_workspace.runtime_validation import validate_runtime_payload


PROFILE = Path(__file__).resolve().parents[1] / "assets/profiles/legacy/Default/slave_one.yaml"


def _simulation() -> SimulationService:
    weapon = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))["weapon"]
    assert validate_runtime_payload(weapon) == []
    states = {
        state["id"]: StateDef(
            id=state["id"],
            on_entry=[ActionDef(action["type"], {k: v for k, v in action.items() if k != "type"})
                      for action in state.get("on_entry", [])],
            on_exit=[ActionDef(action["type"], {k: v for k, v in action.items() if k != "type"})
                     for action in state.get("on_exit", [])],
        )
        for state in weapon["states"]
    }
    transitions = [
        TransitionDef(
            id=transition["id"],
            source=transition["source"],
            target=transition["target"],
            trigger=transition["trigger"],
            internal=transition.get("internal", False),
            actions=[ActionDef(action["type"], {k: v for k, v in action.items() if k != "type"})
                     for action in transition.get("actions", [])],
        )
        for transition in weapon["transitions"]
    ]
    return SimulationService(
        GunConfig(),
        WeaponConfig(initial_state=weapon["initial_state"], states=states, transitions=transitions),
    )


def test_rapid_fire_repeats_without_held_events():
    sim = _simulation()
    first = sim.dispatch_external_event("trigger_pressed")[0].result
    assert first.accepted
    assert first.current_state == "auto_firing"
    assert [c.type for c in first.commands] == ["play_audio", "play_light", "play_light"]
    assert len(sim.runtime.pending_events) == 1

    for _ in range(4):
        events = sim.advance_time(60)
        assert len(events) == 1
        shot = events[0].result
        assert shot.accepted
        assert shot.current_state == "auto_firing"
        assert [c.type for c in shot.commands] == ["play_audio", "play_light"]
        assert shot.commands[0].payload["clip"] in {"audio_0", "audio_1", "audio_2"}
        assert len(sim.runtime.pending_events) == 1


def test_releasing_cancels_next_shot_and_allows_new_press():
    sim = _simulation()
    sim.dispatch_external_event("trigger_pressed")
    sim.advance_time(30)
    sim.dispatch_external_event("trigger_released")
    assert sim.runtime.current_state == "idle"
    assert not sim.runtime.pending_events
    assert sim.advance_time(500) == []

    sim.dispatch_external_event("trigger_pressed")
    sim.advance_time(60)
    sim.dispatch_external_event("trigger_released")
    assert not sim.runtime.pending_events
    assert sim.advance_time(500) == []


def test_generic_cancellation_works_for_all_exit_states():
    for exit_event, expected in (("ammo_empty", "empty"), ("reload_pressed", "reloading")):
        sim = _simulation()
        sim.dispatch_external_event("trigger_pressed")
        sim.dispatch_external_event(exit_event)
        assert sim.runtime.current_state == expected
        assert all(event.event_id != "auto_step" for event in sim.runtime.pending_events)
