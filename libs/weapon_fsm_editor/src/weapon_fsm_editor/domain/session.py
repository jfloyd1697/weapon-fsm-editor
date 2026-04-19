from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SessionDocument:
    path: Optional[Path]
    text: str
    loaded_from_default: bool = False
    warning: Optional[str] = None


@dataclass
class SessionStartupResult:
    gun: SessionDocument
    weapon: SessionDocument
    warnings: list[str]
