from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
CORE_SRC = ROOT / "libs" / "weapon_fsm_core" / "src"
WORKSPACE_SRC = ROOT / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))
if str(WORKSPACE_SRC) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_SRC))

repo_path = CORE_SRC / "weapon_fsm_core" / "infrastructure" / "yaml" / "repositories.py"
spec = spec_from_file_location("demo_profile_repository", repo_path)
repo_module = module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(repo_module)
ProfileRepository = repo_module.ProfileRepository

from weapon_fsm_workspace.examples.preset_director import DemoPresetDirector


def test_demo_presets_roundtrip_save_and_load(tmp_path: Path) -> None:
    director = DemoPresetDirector()
    repo = ProfileRepository()

    demos = {
        "director_full_auto_with_ammo": director.build_full_auto_with_ammo(),
        "director_charge_shot": director.build_charge_shot(),
        "director_burst_shot": director.build_burst_shot(),
    }

    for name, (gun_data, weapon_data) in demos.items():
        gun_path, weapon_path = director.write_demo(tmp_path, name, gun_data, weapon_data)

        loaded_gun = repo.load_gun(gun_path)
        loaded_weapon = repo.load_weapon(weapon_path)

        assert loaded_gun.events
        assert loaded_weapon.initial_state == "ready"
        assert loaded_weapon.states
        assert loaded_weapon.transitions
        assert loaded_weapon.clips
        assert loaded_weapon.light_sequences

    full_auto_weapon = repo.load_weapon(tmp_path / "director_full_auto_with_ammo_weapon.yaml")
    assert full_auto_weapon.variables["ammo"] == 30
    assert "auto_shot" in full_auto_weapon.clips
    assert any(t.id == "reload_done" for t in full_auto_weapon.transitions)

    charge_weapon = repo.load_weapon(tmp_path / "director_charge_shot_weapon.yaml")
    assert charge_weapon.variables["charge_threshold"] == 25
    assert "charge_loop" in charge_weapon.clips
    assert any(t.id == "release_charged" for t in charge_weapon.transitions)

    burst_weapon = repo.load_weapon(tmp_path / "director_burst_shot_weapon.yaml")
    assert burst_weapon.variables["burst_size"] == 3
    assert "burst_shot" in burst_weapon.clips
    assert any(t.id == "continue_burst" for t in burst_weapon.transitions)
