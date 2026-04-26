from pathlib import Path
from typing import Callable

from weapon_fsm_hardware import LightBackend
from ...domain.light_sequence import load_light_sequence


class QtLightBackend(LightBackend):
    def __init__(
        self,
        log: Callable[[str], None] | None = None,
        preview_panel=None,
    ) -> None:
        self._log = log or (lambda message: None)
        self._preview_panel = preview_panel
        self._active_sequence: str | None = None
        self._active_path: Path | None = None

    def play_light(self, *, sequence: str, path: str, mode: str) -> None:
        self._active_sequence = sequence
        self._active_path = Path(path).expanduser()
        self._log(f"[light] play sequence={sequence} mode={mode} path={path}")

        if self._preview_panel is None:
            return

        try:
            asset = load_light_sequence(self._active_path)
            self._preview_panel.play_sequence(
                asset,
                sequence_name=sequence,
                mode=mode,
                asset_path=self._active_path,
            )
        except Exception as exc:  # noqa: BLE001
            self._preview_panel.stop_sequence()
            self._preview_panel.set_status_text(f"Light preview error: {exc}")
            self._log(f"[light] preview error for {sequence}: {exc}")

    def stop_light(self) -> None:
        if self._active_sequence is not None:
            self._log(f"[light] stop sequence={self._active_sequence}")
        self._active_sequence = None
        self._active_path = None
        if self._preview_panel is not None:
            self._preview_panel.stop_sequence()
