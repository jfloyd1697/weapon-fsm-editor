import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

if __package__ is None or __package__ == "":
    # Allows running this file directly from a source checkout.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from weapon_fsm_lights.tools.light_animation_designer.widgets.light_animation_designer_window import \
    LightAnimationDesignerWindow

from pathlib import Path
import faulthandler
import logging
import sys


LOG_DIR = Path.home() / ".weapon_fsm_lights"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "light_animation_designer.log"
FAULT_FILE = LOG_DIR / "light_animation_designer_fault.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

fault_handle = FAULT_FILE.open("a", encoding="utf-8")
faulthandler.enable(file=fault_handle, all_threads=True)

logging.getLogger(__name__).info("Starting Light Animation Designer")

def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = LightAnimationDesignerWindow()
    window.show()
    if len(sys.argv) > 1:
        window.load_project(sys.argv[1])
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
