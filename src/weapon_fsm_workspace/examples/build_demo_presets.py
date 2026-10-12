from pathlib import Path

from weapon_fsm_workspace.examples.preset_director import DemoPresetDirector


def main() -> None:
    director = DemoPresetDirector()
    output_dir = Path(__file__).resolve().parents[1] / "demos"

    demos = {
        "director_full_auto_with_ammo": director.build_full_auto_with_ammo(),
        "director_charge_shot": director.build_charge_shot(),
        "director_burst_shot": director.build_burst_shot(),
    }

    for name, (gun, weapon) in demos.items():
        gun_path, weapon_path = director.write_demo(output_dir, name, gun, weapon)
        print("Wrote {0} and {1}".format(gun_path.name, weapon_path.name))


if __name__ == "__main__":
    main()
