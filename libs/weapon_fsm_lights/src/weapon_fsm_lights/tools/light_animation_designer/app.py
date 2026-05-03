import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

if __package__ is None or __package__ == "":
    # Allows running this file directly from a source checkout.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from weapon_fsm_lights.tools.light_animation_designer.main_window import LightAnimationDesignerWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = LightAnimationDesignerWindow()
    window.show()
    if len(sys.argv) > 1:
        window.load_project(sys.argv[1])
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
