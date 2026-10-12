from pathlib import Path

from weapon_fsm_core.infrastructure.yaml import ProfileYamlMapper

from weapon_fsm_workspace.examples.weapon_preset_director import WeaponPresetDirector


def main() -> int:
    director = WeaponPresetDirector()
    out_dir = Path("generated_presets")
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = "weapon_profile"
    _, weapon = director.build_default_gun()
    weapon_path = Path((out_dir / stem).with_suffix(".yaml"))
    ProfileYamlMapper.write_weapon(weapon, weapon_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
