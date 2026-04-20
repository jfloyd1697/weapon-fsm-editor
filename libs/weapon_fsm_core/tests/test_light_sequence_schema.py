from pathlib import Path

from weapon_fsm_core import load_light_sequence, validate_light_sequence


def test_load_normalized_ring_layout_json(tmp_path: Path) -> None:
    layout_path = tmp_path / "ring_layout.json"
    layout_path.write_text(
        '''{
  "name": "ring",
  "coordinate_space": "normalized_2d",
  "leds": [
    {"index": 0, "u": 0.5, "v": 0.5, "led_radius": 0.02},
    {"index": 1, "u": 0.8, "v": 0.5, "led_radius": 0.02}
  ]
}''',
        encoding="utf-8",
    )

    asset = load_light_sequence(layout_path)

    assert asset.width == 1.0
    assert asset.height == 1.0
    assert [led.id for led in asset.leds] == ["0", "1"]
    assert asset.leds[0].x == 0.5
    assert asset.frames[0].duration_ms == 100


def test_validate_light_sequence_reports_unknown_led_reference(tmp_path: Path) -> None:
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(
        '{"coordinate_space": "normalized_2d", "leds": [{"index": 0, "u": 0.5, "v": 0.5, "led_radius": 0.02}]}',
        encoding="utf-8",
    )
    seq_path = tmp_path / "flash.yaml"
    seq_path.write_text(
        """
layout:
  path: layout.json
frames:
  - leds:
      missing_led: "#ffffff"
""",
        encoding="utf-8",
    )

    errors = validate_light_sequence(seq_path)

    assert errors
    assert "unknown LED 'missing_led'" in errors[0]
