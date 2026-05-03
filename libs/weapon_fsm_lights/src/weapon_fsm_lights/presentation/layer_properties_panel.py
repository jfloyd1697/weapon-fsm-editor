import traceback
from dataclasses import fields, replace
from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QGroupBox, QVBoxLayout, QWidget

from weapon_fsm_lights.domain.animation_layers import (
    LightLayerDef,
    LightLayerType, convert_layer_type,
)
from weapon_fsm_lights.presentation.property_editors import (
    FieldEditor,
    FieldEditorRegistry,
    default_field_editor_registry,
)


class LayerPropertiesPanel(QWidget):
    layer_changed = pyqtSignal(int, object)

    def __init__(
        self,
        *,
        editor_registry: FieldEditorRegistry | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._row: int | None = None
        self._layer: LightLayerDef | None = None
        self._editors: dict[str, FieldEditor] = {}
        self._updating = False
        self._registry = editor_registry or default_field_editor_registry()

        self.form_box = QGroupBox("Layer Properties")
        self.form = QFormLayout(self.form_box)

        layout = QVBoxLayout(self)
        layout.addWidget(self.form_box)
        layout.addStretch(1)

        self.setEnabled(False)

    def set_layer(self, row, layer: LightLayerDef | None) -> None:
        self._row = row
        self._layer = layer
        self.setEnabled(layer is not None)
        self._rebuild()

    def _rebuild(self) -> None:
        self._clear_form()
        self._editors.clear()

        if self._layer is None:
            return

        self._updating = True
        try:
            for field_def in fields(type(self._layer)):
                editor = self._registry.create_editor(field_def)
                value = getattr(self._layer, field_def.name)
                editor.set_value(value)
                editor.value_changed.connect(
                    lambda new_value, name=field_def.name: self._on_field_changed(name, new_value)
                )

                self._editors[field_def.name] = editor
                self.form.addRow(self._label_for(field_def.name), editor)
        except Exception as e:
            traceback.print_exc()
        finally:
            self._updating = False


    def _on_field_changed(self, field_name: str, value: object) -> None:
        if self._updating or self._layer is None:
            return

        if field_name == "type":
            new_type = str(value.value if isinstance(value, LightLayerType) else value)
            self._layer = convert_layer_type(self._layer, new_type)
            self._rebuild()
            self.layer_changed.emit(self._row, self._layer)
            return

        self._layer = replace(self._layer, **{field_name: value})
        self.layer_changed.emit(self._row, self._layer)
        print("layer_changed", self._layer)

    def _clear_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)

    def _label_for(self, field_name: str) -> str:
        return field_name.replace("_", " ").title()

    def clear_layer(self):
        self.set_layer(None, None)