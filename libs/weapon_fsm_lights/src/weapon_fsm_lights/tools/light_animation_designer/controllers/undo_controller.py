from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut

from light_animation_designer.controllers.timeline_controller import Window
from weapon_fsm_lights.tools.light_animation_designer.model.light_designer_undo import UndoRedoKeyFilter


class UndoController:
    def __init__(self, window: Window) -> None:
        self.window = window

    def connect(self) -> None:
        window = self.window

        window.undo_action = window.undo_history.create_undo_action(window, "Undo")
        window.redo_action = window.undo_history.create_redo_action(window, "Redo")

        window.undo_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        window.redo_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)

        window.addAction(window.undo_action)
        window.addAction(window.redo_action)

        window.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), window)
        window.undo_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        window.undo_shortcut.activated.connect(self.undo)

        window.redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), window)
        window.redo_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        window.redo_shortcut.activated.connect(self.redo)

        window.redo_ctrl_y_shortcut = QShortcut(QKeySequence("Ctrl+Y"), window)
        window.redo_ctrl_y_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        window.redo_ctrl_y_shortcut.activated.connect(self.redo)

        window.ui.undo_button.clicked.connect(window.undo_history.stack.undo)
        window.ui.redo_button.clicked.connect(window.undo_history.stack.redo)
        window.undo_history.stack.canUndoChanged.connect(window.ui.undo_button.setEnabled)
        window.undo_history.stack.canRedoChanged.connect(window.ui.redo_button.setEnabled)

        window.ui.undo_button.setEnabled(window.undo_history.stack.canUndo())
        window.ui.redo_button.setEnabled(window.undo_history.stack.canRedo())

    def install_event_filter(self, app) -> None:
        if app is None:
            return

        self.window.undo_redo_key_filter = UndoRedoKeyFilter(
            parent=self.window,
            undo=self.undo,
            redo=self.redo,
        )
        app.installEventFilter(self.window.undo_redo_key_filter)

    def undo(self) -> None:
        self.commit_focused_editor()

        if self.window.undo_history.stack.canUndo():
            self.window.undo_history.stack.undo()

    def redo(self) -> None:
        self.commit_focused_editor()

        if self.window.undo_history.stack.canRedo():
            self.window.undo_history.stack.redo()

    def commit_focused_editor(self) -> None:
        window = self.window
        focused = window.focusWidget()

        if focused is window.ui.animation_name_edit.lineEdit():
            window.animation_controller.apply_controls()
            focused.clearFocus()
            return

        if focused is not None and window.ui.layer_properties.isAncestorOf(focused):
            focused.clearFocus()
