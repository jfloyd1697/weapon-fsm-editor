from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    severity: str = "error"
