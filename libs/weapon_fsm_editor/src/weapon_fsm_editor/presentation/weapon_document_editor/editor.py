from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor, QTextCharFormat
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit

from weapon_fsm_core.domain.model import GunConfig

from .analyzer import WeaponDocumentAnalyzer
from .diagnostics import DiagnosticSeverity, EditorDiagnostic
from .highlighter import WeaponYamlHighlighter


class WeaponDocumentEditor(QPlainTextEdit):
    diagnostics_changed = pyqtSignal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._gun: GunConfig | None = None
        self._analyzer = WeaponDocumentAnalyzer()
        self._diagnostics: list[EditorDiagnostic] = []
        self._highlighter = WeaponYamlHighlighter(self.document())

        self._full_analysis_timer = QTimer(self)
        self._full_analysis_timer.setSingleShot(True)
        self._full_analysis_timer.setInterval(350)
        self._full_analysis_timer.timeout.connect(self._run_full_analysis)

        self._local_analysis_timer = QTimer(self)
        self._local_analysis_timer.setSingleShot(True)
        self._local_analysis_timer.setInterval(125)
        self._local_analysis_timer.timeout.connect(self._run_local_analysis)

        self.textChanged.connect(self._schedule_analysis)

    def set_gun_config(self, gun: GunConfig | None) -> None:
        self._gun = gun
        self._schedule_analysis()

    def diagnostics(self) -> list[EditorDiagnostic]:
        return list(self._diagnostics)

    def goto_line(self, line_number: int) -> None:
        block = self.document().findBlockByLineNumber(line_number)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.centerCursor()

    def _schedule_analysis(self) -> None:
        self._local_analysis_timer.start()
        self._full_analysis_timer.start()

    def _run_local_analysis(self) -> None:
        cursor_line = self.textCursor().blockNumber()
        local_diagnostics = self._analyzer.analyze_local_block(
            self.toPlainText(),
            cursor_line,
            self._gun,
        )
        self._apply_diagnostics(local_diagnostics, local_only=True)

    def _run_full_analysis(self) -> None:
        diagnostics = self._analyzer.analyze_document(self.toPlainText(), self._gun)
        self._apply_diagnostics(diagnostics, local_only=False)
        self.diagnostics_changed.emit(list(self._diagnostics))

    def _apply_diagnostics(
        self,
        diagnostics: list[EditorDiagnostic],
        *,
        local_only: bool,
    ) -> None:
        if local_only and self._diagnostics:
            return

        self._diagnostics = diagnostics
        selections: list[QTextEdit.ExtraSelection] = []

        for diagnostic in diagnostics:
            selection = QTextEdit.ExtraSelection()
            cursor = QTextCursor(self.document().findBlockByLineNumber(diagnostic.line_start))
            if diagnostic.line_end > diagnostic.line_start:
                end_block = self.document().findBlockByLineNumber(diagnostic.line_end)
                cursor.setPosition(
                    end_block.position() + end_block.length() - 1,
                    QTextCursor.MoveMode.KeepAnchor,
                )
            selection.cursor = cursor

            if diagnostic.severity == DiagnosticSeverity.ERROR:
                color = QColor("#ff5f56")
            elif diagnostic.severity == DiagnosticSeverity.WARNING:
                color = QColor("#e6c229")
            else:
                color = QColor("#4ea1ff")

            selection.format.setUnderlineColor(color)
            selection.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
            selections.append(selection)

        self.setExtraSelections(selections)
