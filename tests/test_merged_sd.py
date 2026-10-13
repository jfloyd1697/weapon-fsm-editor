"""Regression coverage for the complete migrated weapon library."""
from pathlib import Path
import yaml

from weapon_fsm_workspace.compiled_assets import decode_manifest
from weapon_fsm_workspace.light_project_compiler import compile_animation_project
from weapon_fsm_workspace.merged_sd import PROFILES, _load_sequence, profiles_by_bank
from weapon_fsm_workspace.runtime_validation import validate_runtime_payload


def _weapon(profile: Path) -> dict:
    document = yaml.safe_load(profile.read_text(encoding="utf-8"))
    weapon = dict(document["weapon"])
    for field in ("clips", "clip_sets", "light_sequences", "audio_effects"):
        if field not in weapon and field in document:
            weapon[field] = document[field]
    return weapon


def test_all_original_weapons_and_added_banks_are_present() -> None:
    banks = profiles_by_bank()
    assert {name: len(profiles) for name, profiles in banks.items()} == {
        "Blaster": 28, "Characters": 11, "Default": 7,
        "Farts": 8, "SciFi": 3, "Tools": 1,
    }
    for profiles in banks.values():
        for profile in profiles:
            assert profile.is_file(), profile
            weapon = _weapon(profile)
            assert validate_runtime_payload(weapon) == [], profile
            for resource in ("clips", "light_sequences"):
                for asset in weapon.get(resource, {}).values():
                    path = asset if isinstance(asset, str) else asset["path"]
                    assert (PROFILES.parents[1] / path).is_file(), (profile, path)


def test_heart_effect_referenced_by_character_heal() -> None:
    heart = PROFILES.parents[1] / "assets/lights/heart_heal_red.yaml"
    data = yaml.safe_load(heart.read_text(encoding="utf-8"))
    assert len(data["frames"]) >= 4
    assert any(frame["leds"] for frame in data["frames"])
    c3 = _weapon(PROFILES / "legacy/Characters/c3p0_hurt.yaml")
    assert any(spec["path"] == "assets/lights/heart_heal_red.yaml"
               for spec in c3["light_sequences"].values())
    for name in ("yoda_hurt", "darth_maul_hurt"):
        data = _weapon(PROFILES / f"{name}.yaml")
        assert data["light_sequences"]["heal_heart"]["path"] == "assets/lights/heart_heal_red.yaml"


def test_metroid_three_shots_use_short_decay() -> None:
    weapon = _weapon(PROFILES / "metroid_prime.yaml")
    short = "prime_regular_shot"
    assert weapon["light_sequences"][short] == "assets/lights/metroid_prime_regular_shot.yaml"
    first = next(s for s in weapon["states"] if s["id"] == "holding")
    action_groups = [first["on_entry"]]
    for transition in weapon["transitions"]:
        if transition["id"] in ("holding_second_burst_shot", "holding_third_burst_shot"):
            action_groups.append(transition["actions"])
    assert len(action_groups) == 3
    assert all(any(a.get("type") == "play_light" and a.get("sequence") == short
                   for a in group) for group in action_groups)

    file = PROFILES.parents[1] / "assets/lights/metroid_prime_regular_shot.yaml"
    raw = yaml.safe_load(file.read_text(encoding="utf-8"))
    assert sum(f["duration_ms"] for f in raw["frames"]) == 180
    peaks = [max((p["intensity"] for p in f["leds"].values()), default=0.0)
             for f in raw["frames"]]
    assert all(a > b for a, b in zip(peaks, peaks[1:]))
    assert 0.0 < peaks[0] < 0.65
    compiled = _load_sequence(file, short)
    assert len(compiled.leds) == 61
    assert len(compiled.frames) == len(raw["frames"])


def test_authored_light_projects_compile_without_gui() -> None:
    file = PROFILES.parents[1] / "assets/lights/metroid-prime-lights.yaml"
    for name in ("prime_charge_warm_build", "prime_charge_warm_hold", "prime_charge_warm_release"):
        compiled = _load_sequence(file, name)
        assert len(compiled.leds) == 61
        assert len(compiled.frames) > 10
        assert any(frame.leds for frame in compiled.frames)
