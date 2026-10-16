"""Regression checks for magazine reloads authored entirely in weapon profiles."""

import wave
from pathlib import Path

import pytest
import yaml

from weapon_fsm_workspace.paths import ASSETS_ROOT, PROFILES_ROOT
from weapon_fsm_workspace.runtime_validation import validate_runtime_payload


@pytest.mark.parametrize(
    ("weapon_name", "capacity", "shell_clip", "pump_clip", "pump_delay_ms"),
    [
        ("sawn_off", 3, "audio_1", "audio_2", 350),
        ("shotgun", 2, "audio_2", "audio_1", 1150),
    ],
)
def test_shells_load_individually_then_pump(
    weapon_name: str,
    capacity: int,
    shell_clip: str,
    pump_clip: str,
    pump_delay_ms: int,
) -> None:
    profile = PROFILES_ROOT / "legacy" / "Default" / f"{weapon_name}.yaml"
    weapon = yaml.safe_load(profile.read_text(encoding="utf-8"))["weapon"]
    assert validate_runtime_payload(weapon) == []
    assert weapon["variables"]["mag_capacity"] == capacity

    states = {state["id"]: state for state in weapon["states"]}
    loading = states["reloading"]["on_entry"]
    pumping = states["pumping"]["on_entry"]
    assert [action["clip"] for action in loading if action["type"] == "play_audio"] == [shell_clip]
    assert [action["clip"] for action in pumping if action["type"] == "play_audio"] == [pump_clip]
    assert [action["delay_ms"] for action in loading if action["type"] == "schedule_event"] == [600]
    assert [action["delay_ms"] for action in pumping if action["type"] == "schedule_event"] == [pump_delay_ms]

    for clip_name, interval_ms in ((shell_clip, 600), (pump_clip, pump_delay_ms)):
        sound = ASSETS_ROOT.parent / weapon["clips"][clip_name]["path"]
        with wave.open(str(sound)) as source:
            clip_duration_ms = 1000 * source.getnframes() / source.getframerate()
        assert clip_duration_ms <= interval_ms, sound

    transitions = {transition["id"]: transition for transition in weapon["transitions"]}
    for source in ("idle", "empty"):
        start = transitions[f"{source}_reload"]
        assert start["guard"] == {"var_lt": {"name": "ammo", "value_from_var": "mag_capacity"}}
        assert start["target"] == "reloading"

    assert transitions["shell_loaded"]["internal"] is True
    assert transitions["shell_loaded"]["actions"] == [
        {"type": "adjust_ammo", "delta": 1},
        {"type": "emit_event", "event": "check_reload"},
    ]
    assert transitions["load_next_shell"]["guard"] == {
        "var_lt": {"name": "ammo", "value_from_var": "mag_capacity"}
    }
    assert transitions["finish_loading"]["guard"] == {
        "var_gte": {"name": "ammo", "value_from_var": "mag_capacity"}
    }
    assert transitions["finish_loading"]["target"] == "pumping"
    assert transitions["pumping_complete"]["target"] == "idle"
    assert all(
        action["type"] != "set_ammo_full"
        for state in states.values()
        for action in state.get("on_entry", []) + state.get("on_exit", [])
    )
