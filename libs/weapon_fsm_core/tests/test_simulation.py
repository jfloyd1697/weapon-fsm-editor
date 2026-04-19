from pathlib import Path

from weapon_fsm_core.application.simulate_event import SimulationService
from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository


def _load_demo() -> SimulationService:
    demo_dir = Path(__file__).resolve().parents[3] / "demos"
    repo = ProfileRepository()
    gun = repo.load_gun(demo_dir / "default_gun.yaml")
    weapon = repo.load_weapon(demo_dir / "weapon_profile.yaml")
    return SimulationService(gun, weapon)


def test_trigger_pressed_enters_charging_and_starts_loop() -> None:
    simulation = _load_demo()

    records = simulation.dispatch_external_event("trigger_pressed")

    assert simulation.runtime.current_state == "charging"
    commands = [cmd for record in records for cmd in record.result.commands]
    play_loop = next(cmd for cmd in commands if cmd.type == "play_audio_loop")
    assert play_loop.payload["clip"] == "charge_loop"
    assert play_loop.payload["interrupt"] == "ignore"


def test_advance_time_completes_reload_to_ready() -> None:
    simulation = _load_demo()
    simulation.runtime.ammo_count = 0
    simulation.runtime.current_state = "empty"

    simulation.dispatch_external_event("on_reload")
    records = simulation.advance_time(1200)

    assert simulation.runtime.current_state == "ready"
    assert simulation.runtime.ammo_count == simulation.runtime.weapon.mag_capacity
    assert any(record.result.transition and record.result.transition.id == "reload_done" for record in records)
