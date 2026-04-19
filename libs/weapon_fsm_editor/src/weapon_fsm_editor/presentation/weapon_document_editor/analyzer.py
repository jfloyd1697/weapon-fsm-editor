from __future__ import annotations

from dataclasses import dataclass

import yaml
from yaml.error import MarkedYAMLError

from weapon_fsm_core.domain.model import GunConfig, WeaponConfig
from weapon_fsm_core.domain.validation import ProfileValidator, ValidationIssue
from weapon_fsm_core.infrastructure.yaml.repositories import ProfileRepository

from .diagnostics import DiagnosticSeverity, EditorDiagnostic


@dataclass(frozen=True)
class BlockSpan:
    path: str
    line_start: int
    line_end: int


class WeaponDocumentAnalyzer:
    def __init__(
        self,
        repository: ProfileRepository | None = None,
        validator: ProfileValidator | None = None,
    ) -> None:
        self._repository = repository or ProfileRepository()
        self._validator = validator or ProfileValidator()

    def analyze_document(
        self,
        text: str,
        gun: GunConfig | None,
    ) -> list[EditorDiagnostic]:
        diagnostics: list[EditorDiagnostic] = []
        block_spans = self._build_block_spans(text)

        try:
            yaml.safe_load(text or "")
        except MarkedYAMLError as exc:
            line = exc.problem_mark.line if exc.problem_mark is not None else 0
            message = exc.problem or str(exc)
            diagnostics.append(
                EditorDiagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    message=message,
                    line_start=line,
                    line_end=line,
                )
            )
            return diagnostics
        except Exception as exc:
            diagnostics.append(
                EditorDiagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    message=str(exc),
                    line_start=0,
                    line_end=0,
                )
            )
            return diagnostics

        try:
            weapon = self._repository.load_weapon_text(text)
        except Exception as exc:
            diagnostics.append(
                EditorDiagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    message=str(exc),
                    line_start=0,
                    line_end=0,
                    path="weapon",
                )
            )
            return diagnostics

        diagnostics.extend(self.analyze_weapon_config(weapon, gun, block_spans))
        return diagnostics

    def analyze_weapon_config(
        self,
        weapon: WeaponConfig,
        gun: GunConfig | None,
        block_spans: list[BlockSpan] | None = None,
    ) -> list[EditorDiagnostic]:
        if gun is None:
            return []

        block_spans = block_spans or []
        issues = self._validator.validate(gun, weapon)
        return [self._issue_to_diagnostic(issue, block_spans) for issue in issues]

    def analyze_local_block(
        self,
        text: str,
        cursor_line: int,
        gun: GunConfig | None,
    ) -> list[EditorDiagnostic]:
        block = self._extract_local_block(text, cursor_line)
        if not block.strip():
            return []
        return self.analyze_document(block, gun)

    def _issue_to_diagnostic(
        self,
        issue: ValidationIssue,
        block_spans: list[BlockSpan],
    ) -> EditorDiagnostic:
        for span in block_spans:
            if issue.path == span.path or issue.path.startswith(span.path + "."):
                return EditorDiagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    message=issue.message,
                    line_start=span.line_start,
                    line_end=span.line_end,
                    path=issue.path,
                )

        return EditorDiagnostic(
            severity=DiagnosticSeverity.ERROR,
            message=issue.message,
            line_start=0,
            line_end=0,
            path=issue.path,
        )

    def _build_block_spans(self, text: str) -> list[BlockSpan]:
        lines = text.splitlines()
        spans: list[BlockSpan] = []

        root_sections: dict[str, int] = {}
        weapon_start = None
        state_section_start = None
        transition_section_start = None

        for index, line in enumerate(lines):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))
            if indent == 0 and stripped.endswith(":"):
                root_sections[stripped[:-1]] = index
            if stripped == "weapon:":
                weapon_start = index
            elif stripped == "states:" and indent == 2:
                state_section_start = index
            elif stripped == "transitions:" and indent == 2:
                transition_section_start = index

        if weapon_start is not None:
            spans.append(BlockSpan("weapon", weapon_start, max(weapon_start, len(lines) - 1)))

        for section_name in ("clips", "light_sequences"):
            section_start = root_sections.get(section_name)
            if section_start is None:
                continue
            spans.append(BlockSpan(section_name, section_start, max(section_start, len(lines) - 1)))
            spans.extend(self._scan_mapping_blocks(lines, section_start, section_name))

        spans.extend(self._scan_named_list_blocks(lines, state_section_start, "weapon.states"))
        spans.extend(self._scan_named_list_blocks(lines, transition_section_start, "weapon.transitions"))
        return spans

    def _scan_mapping_blocks(
        self,
        lines: list[str],
        section_start: int,
        prefix: str,
    ) -> list[BlockSpan]:
        spans: list[BlockSpan] = []
        current_name: str | None = None
        current_start: int | None = None
        section_indent = len(lines[section_start]) - len(lines[section_start].lstrip(" "))

        def flush(end_line: int) -> None:
            nonlocal current_name, current_start
            if current_name is None or current_start is None:
                return
            spans.append(BlockSpan(f"{prefix}.{current_name}", current_start, end_line))
            current_name = None
            current_start = None

        for index in range(section_start + 1, len(lines)):
            line = lines[index]
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))
            if not stripped:
                continue
            if indent <= section_indent:
                flush(index - 1)
                break
            if indent == section_indent + 2 and stripped.endswith(":"):
                flush(index - 1)
                current_name = stripped[:-1]
                current_start = index

        flush(len(lines) - 1)
        return spans

    def _scan_named_list_blocks(
        self,
        lines: list[str],
        section_start: int | None,
        prefix: str,
    ) -> list[BlockSpan]:
        if section_start is None:
            return []

        spans: list[BlockSpan] = []
        current_id: str | None = None
        current_start: int | None = None
        section_indent = len(lines[section_start]) - len(lines[section_start].lstrip(" "))

        def flush(end_line: int) -> None:
            nonlocal current_id, current_start
            if current_id is None or current_start is None:
                return
            spans.append(BlockSpan(f"{prefix}.{current_id}", current_start, end_line))
            current_id = None
            current_start = None

        for index in range(section_start + 1, len(lines)):
            line = lines[index]
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))

            if indent <= section_indent and stripped:
                flush(index - 1)
                break

            if stripped.startswith("- id:") and indent == section_indent + 2:
                flush(index - 1)
                current_id = stripped.split(":", 1)[1].strip()
                current_start = index

        flush(len(lines) - 1)
        return spans

    def _extract_local_block(self, text: str, cursor_line: int) -> str:
        lines = text.splitlines()
        if not lines:
            return ""

        cursor_line = max(0, min(cursor_line, len(lines) - 1))
        start = cursor_line
        end = cursor_line

        while start > 0 and not lines[start].lstrip().startswith("- id:"):
            start -= 1

        while end + 1 < len(lines):
            next_line = lines[end + 1]
            if next_line.lstrip().startswith("- id:") and (
                len(next_line) - len(next_line.lstrip(" "))
            ) <= (len(lines[start]) - len(lines[start].lstrip(" "))):
                break
            if next_line and not next_line.startswith(" "):
                break
            end += 1

        return "\n".join(lines[start:end + 1])
