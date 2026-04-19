from __future__ import annotations

from pathlib import Path


def resolve_asset_path(weapon_file: str | Path, asset_path: str) -> Path:
    weapon_path = Path(weapon_file)
    candidate = Path(asset_path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (weapon_path.parent / candidate).resolve()
