from PyQt6.QtCore import QSignalBlocker

from .light_designer_timeline_sync import LightDesignerTimelineSync


class Window:
    def __init__(self) -> None:
        self.animation_controller = None
        self.SETTINGS_LAST_PROJECT = None
        self.project_path = None
        self.MAX_RECENT_PROJECTS = None
        self.recent_project_paths = None
        self.SETTINGS_RECENT_PROJECTS = None
        self.settings = None
        self.layout_asset = None
        self.updating_lists = None
        self.selected_animation = None
        self.layer_enabled_by_animation = None
        self.updating_controls = None
        self.timeline_controller = None
        self.project = None
        self.layer_controller = None
        self.preview_controller = None
        self.undo_history = None
        self.selected_layer_index = None
        self.context = None
        self.ui = None

    def record_undo(self, label, undo_before):
        pass

    def addAction(self, redo_action):
        pass

    def focusWidget(self):
        pass


class TimelineController:
    def __init__(self, window: Window) -> None:
        self.window = window
        self.sync = LightDesignerTimelineSync(window.ui.timeline)
        self.undo_before = None

    def connect(self) -> None:
        timeline = self.window.ui.timeline
        timeline.edit_started.connect(self.begin_edit)
        timeline.edit_finished.connect(self.finish_edit)
        timeline.duration_changed.connect(self.on_duration_changed)
        timeline.layer_timing_changed.connect(self.on_layer_timing_changed)
        timeline.selected_layer_changed.connect(self.window.ui.layer_list.setCurrentRow)

    def refresh(self) -> None:
        animation = self.window.context.current_animation()

        enabled = []
        if animation is not None:
            enabled = self.window.context.layer_enabled_for_animation(animation)

        self.sync.refresh(
            animation=animation,
            selected_layer_index=self.window.selected_layer_index,
            enabled_layers=enabled,
        )

    def set_selected_layer(self, selected_layer_index: int | None) -> None:
        self.sync.set_selected_layer(selected_layer_index)

    def begin_edit(self) -> None:
        self.undo_before = self.window.undo_history.snapshot()

    def finish_edit(self, label: str) -> None:
        if self.undo_before is None:
            return

        self.window.record_undo(label, self.undo_before)
        self.undo_before = None
        self.refresh()

    def on_duration_changed(self, duration_ms: int) -> None:
        animation = self.window.context.current_animation()

        if animation is None:
            return

        animation.duration_ms = duration_ms

        with QSignalBlocker(self.window.ui.animation_duration_ms):
            self.window.ui.animation_duration_ms.setValue(duration_ms)

        self.window.preview_controller.recompile(autoplay=self.window.ui.player.is_playing)

    def on_layer_timing_changed(
        self,
        row: int,
        start_ms: int,
        duration_ms: int,
    ) -> None:
        animation = self.window.context.current_animation()

        if animation is None:
            return

        if not (0 <= row < len(animation.layers)):
            return

        layer = animation.layers[row]
        layer.start_ms = start_ms
        layer.duration_ms = duration_ms

        if row == self.window.selected_layer_index:
            self.window.layer_controller.load_controls()

        self.window.preview_controller.recompile(autoplay=self.window.ui.player.is_playing)
