"""Regression checks for the compiled, timed True Jedi weapon profile."""

from pathlib import Path

import yaml

from weapon_fsm_workspace.runtime_validation import validate_runtime_payload


PROFILE = (
    Path(__file__).resolve().parents[1]
    / "assets/profiles/legacy/Characters/true_jedi.yaml"
)


def test_true_jedi_advances_by_timer_not_repeated_trigger_presses() -> None:
    weapon = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))["weapon"]
    assert weapon["initial_state"] == "studs_00"
    assert weapon["variables"]["progress_interval_ms"] == 400
    assert weapon["variables"]["completion_hold_ms"] >= 1109
    assert len(weapon["light_sequences"]) == 1
    assert validate_runtime_payload(weapon) == []

    transitions = weapon["transitions"]
    start = [step for step in transitions if step["trigger"] == "trigger_pressed"]
    assert len(start) == 1
    assert start[0]["source"] == "studs_00"
    assert start[0]["target"] == "studs_01"

    states = {state["id"]: state for state in weapon["states"]}
    assert len(states) == 21
    for stage in range(1, 20):
        state_id = f"studs_{stage:02d}"
        schedule = next(action for action in states[state_id]["on_entry"]
                        if action["type"] == "schedule_event")
        assert schedule["event"] == "progress_tick"
        assert schedule["delay_ms_from_var"] == "progress_interval_ms"
        advance = [step for step in transitions if step["source"] == state_id
                   and step["trigger"] == "progress_tick"]
        assert len(advance) == 1
        assert advance[0]["guard"] == {"trigger_pressed": True}
        assert advance[0]["target"] == f"studs_{stage + 1:02d}"
        assert any(step["trigger"] == "trigger_released" and step["target"] == "studs_00"
                   for step in transitions if step["source"] == state_id)

    completion = states["studs_20"]["on_entry"]
    assert any(action["type"] == "schedule_event" and action["event"] == "completion_done"
               for action in completion)
    assert any(step["source"] == "studs_20" and step["trigger"] == "completion_done"
               and step["target"] == "studs_00" for step in transitions)
