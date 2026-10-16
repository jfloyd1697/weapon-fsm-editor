"""The preview must not reparse its lighting YAML for every rapid-fire shot."""

from pathlib import Path
from unittest.mock import MagicMock

from weapon_fsm_lights.infrastructure.runtime import qt_light_backend


def test_light_preview_caches_sequence_until_file_changes(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "flash.yaml"
    path.write_text("first", encoding="utf-8")
    loader = MagicMock(return_value=object())
    monkeypatch.setattr(qt_light_backend, "load_light_sequence", loader)
    panel = MagicMock()
    backend = qt_light_backend.QtLightBackend(preview_panel=panel)

    for _ in range(20):
        backend.play_light(sequence="flash", path=str(path))
    assert loader.call_count == 1
    assert panel.play_sequence.call_count == 20

    path.write_text("changed content", encoding="utf-8")
    backend.play_light(sequence="flash", path=str(path))
    assert loader.call_count == 2
