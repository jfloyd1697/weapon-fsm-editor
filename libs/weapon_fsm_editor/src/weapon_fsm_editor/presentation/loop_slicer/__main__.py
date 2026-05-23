from qtpy import QtWidgets

from weapon_fsm_editor.presentation.loop_slicer.loop_slicer_widget import LoopSampleEditorWidget


def main() -> int:
    app = QtWidgets.QApplication([])

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Loop Sample Editor")

    editor = LoopSampleEditorWidget()
    window.setCentralWidget(editor)
    window.resize(1100, 420)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
