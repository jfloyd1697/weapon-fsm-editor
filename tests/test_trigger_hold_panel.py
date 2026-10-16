"""The editor must keep emitting held input while the trigger is pressed."""

import pytest


def test_trigger_hold_repeats_until_release() -> None:
    pytest.importorskip("qtpy.QtWidgets")
    from qtpy.QtWidgets import QApplication

    from weapon_fsm_editor.presentation.panels.gun_control_panel import GunControlPanel

    app = QApplication.instance() or QApplication([])
    panel = GunControlPanel()
    try:
        assert not panel._hold_timer.isSingleShot()
        assert panel._hold_timer.interval() == 100
    finally:
        panel.close()
