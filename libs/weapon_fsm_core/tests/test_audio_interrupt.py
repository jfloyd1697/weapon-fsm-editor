from pathlib import Path

from weapon_fsm_core.application.simulate_event import SimulationService
from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository


def _load_demo() -> SimulationService:
    demo_dir = Path(__file__).resolve().parents[3] / "demos"
    repo = ProfileRepository()
    gun = repo.load_gun(demo_dir / "default_gun.yaml")
    weapon = repo.load_weapon(demo_dir / "weapon_profile.yaml")
    return SimulationService(gun, weapon)


def test_charge_loop_defaults_to_ignore_interrupt_policy_when_specified() -> None:
    simulation = _load_demo()
    records = simulation.dispatch_external_event("trigger_pressed")
    commands = [cmd for record in records for cmd in record.result.commands]

    play_loop = next(cmd for cmd in commands if cmd.type == "play_audio_loop")
    assert play_loop.payload["interrupt"] == "ignore"
    assert play_loop.payload["clip"] == "charge_loop"


def test_stop_audio_emitted_on_charge_exit() -> None:
    simulation = _load_demo()
    simulation.dispatch_external_event("trigger_pressed")
    records = simulation.dispatch_external_event("trigger_released")
    commands = [cmd for record in records for cmd in record.result.commands]

    stop = next(cmd for cmd in commands if cmd.type == "stop_audio")
    assert stop.payload["clip"] == "charge_loop"


def test_charge_done_only_fires_when_trigger_still_pressed() -> None:
    simulation = _load_demo()
    simulation.dispatch_external_event("trigger_pressed")
    simulation.dispatch_external_event("trigger_released")
    records = simulation.advance_time(500)

    assert simulation.runtime.current_state == "ready"
    assert not any(record.result.accepted and record.result.event_id == "charge_done" for record in records)
