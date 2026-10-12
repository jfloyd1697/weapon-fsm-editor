from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QAction, QKeyEvent, QUndoCommand, QUndoStack
from PyQt6.QtWidgets import QWidget


StateT = TypeVar("StateT")


class SnapshotUndoCommand(QUndoCommand):
    def __init__(
        self,
        *,
        text: str,
        before: object,
        after: object,
        restore_state: Callable[[object], None],
        set_restoring: Callable[[bool], None],
    ) -> None:
        super().__init__(text)
        self._before = before
        self._after = after
        self._restore_state = restore_state
        self._set_restoring = set_restoring
        self._first_redo = True

    def undo(self) -> None:
        self._apply(self._before)

    def redo(self) -> None:
        if self._first_redo:
            self._first_redo = False
            return

        self._apply(self._after)

    def _apply(self, state: object) -> None:
        self._set_restoring(True)

        try:
            self._restore_state(state)
        finally:
            self._set_restoring(False)


class SnapshotUndoHistory(Generic[StateT]):
    def __init__(
        self,
        *,
        parent: QWidget,
        capture_state: Callable[[], StateT],
        restore_state: Callable[[StateT], None],
    ) -> None:
        self._capture_state = capture_state
        self._restore_state = restore_state
        self._is_restoring = False
        self.stack = QUndoStack(parent)

    @property
    def is_restoring(self) -> bool:
        return self._is_restoring

    def snapshot(self) -> StateT:
        return self._capture_state()

    def record(self, text: str, before: StateT) -> None:
        if self._is_restoring:
            return

        after = self._capture_state()

        if before == after:
            return

        self.stack.push(
            SnapshotUndoCommand(
                text=text,
                before=before,
                after=after,
                restore_state=self._restore_state_object,
                set_restoring=self._set_restoring,
            )
        )

    def clear(self) -> None:
        self.stack.clear()

    def create_undo_action(self, parent: QWidget, text: str = "Undo") -> QAction:
        return self.stack.createUndoAction(parent, text)

    def create_redo_action(self, parent: QWidget, text: str = "Redo") -> QAction:
        return self.stack.createRedoAction(parent, text)

    def _restore_state_object(self, state: object) -> None:
        self._restore_state(state)

    def _set_restoring(self, value: bool) -> None:
        self._is_restoring = value


class UndoRedoKeyFilter(QObject):
    def __init__(
        self,
        *,
        parent: QObject,
        undo: Callable[[], None],
        redo: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._undo = undo
        self._redo = redo

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.KeyPress:
            return False

        if not isinstance(event, QKeyEvent):
            return False

        modifiers = event.modifiers()
        key = event.key()

        is_ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        is_shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        if not is_ctrl:
            return False

        if key == Qt.Key.Key_Z and is_shift:
            self._redo()
            return True

        if key == Qt.Key.Key_Z:
            self._undo()
            return True

        if key == Qt.Key.Key_Y:
            self._redo()
            return True

        return False
