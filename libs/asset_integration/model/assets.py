from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClipDef:
    name: str
    path: str
    preload: bool = True


@dataclass(frozen=True)
class LightSequenceDef:
    name: str
    path: str
    preload: bool = True
