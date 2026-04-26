from pathlib import Path

from weapon_fsm_core import ProfileYamlBuilder
from weapon_fsm_workspace.examples.weapon_preset_director import WeaponPresetDirector


def main() -> int:
    director = WeaponPresetDirector()
    out_dir = Path("generated_presets")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_profiles = director.build_all()
    for stem, weapon in all_profiles.items():
        path = (out_dir / stem).with_suffix(".yaml")
        with open(path, "w") as f:
            f.write(ProfileYamlBuilder().dump_weapon(weapon))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
