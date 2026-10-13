import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from weapon_fsm_editor.presentation.main_window import MainWindow


def main() -> int:
    from weapon_fsm_workspace.paths import PROFILES_ROOT
    app = QApplication(sys.argv)
    gun_path = Path(sys.argv[1]) if len(sys.argv) > 1 else PROFILES_ROOT / "default_gun.yaml"
    weapon_path = Path(sys.argv[2]) if len(sys.argv) > 2 else PROFILES_ROOT / "weapon_profile.yaml"
    window = MainWindow(gun_path, weapon_path)
    window.resize(1600, 950)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
