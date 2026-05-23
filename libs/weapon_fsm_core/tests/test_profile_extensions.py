from pathlib import Path

from weapon_fsm_core import ProfileRepository, ProfileValidator
from weapon_fsm_lights import LightsProfileExtension


def test_lights_extension_loads_sequences_from_top_level_lights(tmp_path: Path) -> None:
    repo = ProfileRepository(extensions=[LightsProfileExtension()])
    weapon = repo.load_weapon_text(
        """
            weapon:
              initial_state: idle
              states:
                - id: idle
                  label: Idle
              transitions: []
            lights:
              sequences:
                charge_glow:
                  path: lights/charge_glow.yaml
            """,
        source_path=tmp_path / "weapon.yaml",
    )

    assert "charge_glow" in weapon.light_sequences
    assert weapon.subsystems["lights"]["sequences"]["charge_glow"]["path"] == "lights/charge_glow.yaml"


def test_lights_extension_participates_in_validation(tmp_path: Path) -> None:
    lights_dir = tmp_path / "lights"
    lights_dir.mkdir()
    (lights_dir / "charge_glow.yaml").write_text(
        """
            layout:
              width: 1
              height: 1
              leds:
                - id: a
                  x: 0.5
                  y: 0.5
            frames:
              - leds:
                  b: "#ffffff"
        """,
        encoding="utf-8",
    )
    repo = ProfileRepository(extensions=[LightsProfileExtension()])
    validator = ProfileValidator(extensions=[LightsProfileExtension()])
    weapon = repo.load_weapon_text(
        """
            weapon:
              initial_state: idle
              states:
                - id: idle
                  label: Idle
                  on_entry:
                    - type: play_light
                      sequence: charge_glow
              transitions: []
            lights:
              sequences:
                charge_glow:
                  path: lights/charge_glow.yaml
            """,
        source_path=tmp_path / "weapon.yaml",
    )
    gun = repo.load_gun_text("gun: {events: []}")
    issues = validator.validate(gun, weapon)

    assert any("unknown LED 'b'" in issue.message for issue in issues)
