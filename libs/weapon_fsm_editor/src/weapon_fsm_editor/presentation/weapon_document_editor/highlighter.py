from __future__ import annotations

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QSyntaxHighlighter


class WeaponYamlHighlighter(QSyntaxHighlighter):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#7aa2f7"))
        key_format.setFontWeight(QFont.Weight.Bold)

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#9ece6a"))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#ff9e64"))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#565f89"))
        comment_format.setFontItalic(True)

        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#bb9af7"))

        self._rules.extend(
            [
                (QRegularExpression(r"^\s*[^#\-][^:]*:"), key_format),
                (QRegularExpression(r"\b(true|false)\b"), bool_format),
                (QRegularExpression(r"\b\d+\b"), number_format),
                (QRegularExpression(r"'[^']*'"), string_format),
                (QRegularExpression(r'"[^"]*"'), string_format),
                (QRegularExpression(r"#.*$"), comment_format),
            ]
        )

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
