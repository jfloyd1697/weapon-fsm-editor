from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class WeaponProfileExtensionData:
    values: dict[str, Any] = field(default_factory=dict)
    references: dict[str, set[str]] = field(default_factory=dict)


class WeaponProfileExtension(Protocol):
    key: str

    def load_weapon_node(self, node: Any, *, source_path: Path | None) -> WeaponProfileExtensionData:
        ...

    def validate_weapon_node(self, weapon: Any, *, source_path: Path | None) -> list[tuple[str, str]]:
        ...
