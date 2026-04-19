from dataclasses import dataclass
from enum import Enum


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class EditorDiagnostic:
    severity: DiagnosticSeverity
    message: str
    line_start: int
    line_end: int
    column_start: int | None = None
    column_end: int | None = None
    path: str | None = None

    def contains_line(self, line_number: int) -> bool:
        return self.line_start <= line_number <= self.line_end
