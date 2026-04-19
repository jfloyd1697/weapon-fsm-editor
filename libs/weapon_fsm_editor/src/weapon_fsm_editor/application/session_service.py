from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings


@dataclass
class SessionDocument:
    path: Optional[Path]
    text: str
    loaded_from_default: bool = False


@dataclass
class SessionStartupResult:
    gun: SessionDocument
    weapon: SessionDocument
    warnings: list[str]


class SessionService:
    _SETTINGS_RECENT_WEAPONS_KEY = "recent_weapon_files"
    _SETTINGS_LAST_GUN_KEY = "last_gun_file"

    def __init__(self, settings: QSettings, default_gun_path: Path) -> None:
        self._settings = settings
        self._default_gun_path = default_gun_path
        self._weapon_path: Optional[Path] = None
        self._gun_path: Optional[Path] = None

    @property
    def weapon_path(self) -> Optional[Path]:
        return self._weapon_path

    @property
    def gun_path(self) -> Optional[Path]:
        return self._gun_path

    @property
    def default_gun_path(self) -> Path:
        return self._default_gun_path

    def preferred_weapon_dialog_directory(self) -> Path:
        if self._weapon_path is not None:
            return self._weapon_path.parent
        latest = self.latest_recent_weapon_path()
        if latest is not None:
            return latest.parent
        return Path.cwd()

    def preferred_gun_dialog_directory(self) -> Path:
        if self._gun_path is not None:
            return self._gun_path.parent
        last = self.last_gun_path()
        if last is not None:
            return last.parent
        return self._default_gun_path.parent

    def startup(self, requested_weapon_path: Optional[Path] = None, requested_gun_path: Optional[Path] = None) -> SessionStartupResult:
        warnings: list[str] = []
        gun_doc = self._resolve_gun_document(requested_gun_path, warnings)
        weapon_doc = self._resolve_weapon_document(requested_weapon_path, warnings)
        return SessionStartupResult(gun=gun_doc, weapon=weapon_doc, warnings=warnings)

    def _resolve_gun_document(self, requested_gun_path: Optional[Path], warnings: list[str]) -> SessionDocument:
        candidates: list[Path] = []
        if requested_gun_path is not None:
            candidates.append(requested_gun_path)
        last = self.last_gun_path()
        if last is not None and last not in candidates:
            candidates.append(last)
        if self._default_gun_path not in candidates:
            candidates.append(self._default_gun_path)
        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8")
                self._gun_path = path
                self.set_last_gun_path(path)
                return SessionDocument(path=path, text=text, loaded_from_default=(path == self._default_gun_path))
            except Exception:
                warnings.append(f"Failed to load gun file: {path}")
        raise RuntimeError(f"Failed to load default gun file: {self._default_gun_path}")

    def _resolve_weapon_document(self, requested_weapon_path: Optional[Path], warnings: list[str]) -> SessionDocument:
        candidates: list[Path] = []
        if requested_weapon_path is not None:
            candidates.append(requested_weapon_path)
        latest = self.latest_recent_weapon_path()
        if latest is not None and latest not in candidates:
            candidates.append(latest)
        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8")
                self._weapon_path = path
                self.add_recent_weapon_path(path)
                return SessionDocument(path=path, text=text)
            except Exception:
                warnings.append(f"Failed to load weapon file: {path}")
        self._weapon_path = None
        return SessionDocument(path=None, text="")

    def load_weapon(self, path: Path) -> SessionDocument:
        text = path.read_text(encoding="utf-8")
        self._weapon_path = path
        self.add_recent_weapon_path(path)
        return SessionDocument(path=path, text=text)

    def load_gun(self, path: Path) -> SessionDocument:
        try:
            text = path.read_text(encoding="utf-8")
            self._gun_path = path
            self.set_last_gun_path(path)
            return SessionDocument(path=path, text=text)
        except Exception:
            default_text = self._default_gun_path.read_text(encoding="utf-8")
            self._gun_path = self._default_gun_path
            self.set_last_gun_path(self._default_gun_path)
            return SessionDocument(path=self._default_gun_path, text=default_text, loaded_from_default=True)

    def save_weapon(self, text: str, path: Optional[Path] = None) -> Path:
        target = path or self._weapon_path
        if target is None:
            raise RuntimeError("No weapon path is set")
        target.write_text(text, encoding="utf-8")
        self._weapon_path = target
        self.add_recent_weapon_path(target)
        return target

    def save_gun(self, text: str, path: Optional[Path] = None) -> Path:
        target = path or self._gun_path
        if target is None:
            raise RuntimeError("No gun path is set")
        target.write_text(text, encoding="utf-8")
        self._gun_path = target
        self.set_last_gun_path(target)
        return target

    def recent_weapon_paths(self) -> list[Path]:
        value = self._settings.value(self._SETTINGS_RECENT_WEAPONS_KEY, [])
        if isinstance(value, str):
            items = [value] if value else []
        else:
            items = [str(item) for item in value]
        return [Path(item) for item in items]

    def add_recent_weapon_path(self, path: Path) -> None:
        resolved = path.resolve()
        items = [str(resolved)]
        for existing in self.recent_weapon_paths():
            if existing.resolve() != resolved:
                items.append(str(existing.resolve()))
        self._settings.setValue(self._SETTINGS_RECENT_WEAPONS_KEY, items[:10])

    def remove_recent_weapon_path(self, path: Path) -> None:
        resolved = path.resolve()
        items = [str(existing.resolve()) for existing in self.recent_weapon_paths() if existing.resolve() != resolved]
        self._settings.setValue(self._SETTINGS_RECENT_WEAPONS_KEY, items)

    def latest_recent_weapon_path(self) -> Optional[Path]:
        for path in self.recent_weapon_paths():
            if path.exists():
                return path
        return None

    def last_gun_path(self) -> Optional[Path]:
        value = self._settings.value(self._SETTINGS_LAST_GUN_KEY)
        if not value:
            return None
        path = Path(str(value))
        return path if path.exists() else None

    def set_last_gun_path(self, path: Path) -> None:
        self._settings.setValue(self._SETTINGS_LAST_GUN_KEY, str(path.resolve()))
