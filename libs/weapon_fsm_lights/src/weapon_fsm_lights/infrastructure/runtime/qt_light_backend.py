from pathlib import Path
from typing import Callable

from weapon_fsm_core.domain.enums import LightMode
from weapon_fsm_hardware import LightBackend
from weapon_fsm_lights import load_light_sequence


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
        self._sequence_cache: dict[Path, tuple[int, int, object]] = {}

    def play_light(self, *, sequence: str, path: str, mode: str = LightMode.ONCE) -> None:
        self._active_sequence = sequence
        self._active_path = Path(path).expanduser()
        self._log(f"[light] play sequence={sequence} mode={mode} path={path}")

        if self._preview_panel is None:
            return

        try:
            path = self._active_path.resolve()
            stat = path.stat()
            cached = self._sequence_cache.get(path)
            if cached is None or cached[:2] != (stat.st_mtime_ns, stat.st_size):
                asset = load_light_sequence(path)
                self._sequence_cache[path] = (stat.st_mtime_ns, stat.st_size, asset)
            else:
                asset = cached[2]
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
