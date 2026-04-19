from pathlib import Path

from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository


def test_repository_loads_demo_files() -> None:
    demo_dir = Path(__file__).resolve().parents[3] / "demos"
    repo = ProfileRepository()
    gun = repo.load_gun(demo_dir / "default_gun.yaml")
    weapon = repo.load_weapon(demo_dir / "weapon_profile.yaml")

    assert "trigger_pressed" in gun.events
    assert weapon.mag_capacity == 5
    assert weapon.initial_state == "ready"
    assert "ready" in weapon.states
