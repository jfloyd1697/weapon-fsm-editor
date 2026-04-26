import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class WeaponProfileExtensionData:
    values: dict[str, Any] = field(default_factory=dict)
    references: dict[str, set[str]] = field(default_factory=dict)


class WeaponProfileExtension(abc.ABC):
    key: str

    @abc.abstractmethod
    def load_weapon_node(self, node: Any, *, source_path: Path | None) -> WeaponProfileExtensionData:
        ...

    @abc.abstractmethod
    def validate_weapon_node(self, weapon: Any, *, source_path: Path | None) -> list[tuple[str, str]]:
        ...
