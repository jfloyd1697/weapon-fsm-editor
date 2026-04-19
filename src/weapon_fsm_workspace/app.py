import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from weapon_fsm_editor.presentation.main_window import MainWindow


def main() -> int:
    root = Path(__file__).parent
    app = QApplication(sys.argv)
    gun_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "demos" / "default_gun.yaml"
    weapon_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "demos" / "weapon_profile.yaml"
    window = MainWindow(gun_path, weapon_path)
    window.resize(1600, 950)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
