from dataclasses import Field
from typing import Any, Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget, QCheckBox,
)

from weapon_fsm_lights.domain.animation_layers import LightLayerType


class FieldEditor(QWidget):
    value_changed = pyqtSignal(object)

    def value(self) -> object:
        raise NotImplementedError

    def set_value(self, value: object) -> None:
        raise NotImplementedError


class TextEditor(FieldEditor):
    def __init__(self) -> None:
        super().__init__()
        self.edit = QLineEdit()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit)
        self.edit.editingFinished.connect(lambda: self.value_changed.emit(self.edit.text()))

    def value(self) -> object:
        return self.edit.text()

    def set_value(self, value: object) -> None:
        self.edit.setText("" if value is None else str(value))


class IntEditor(FieldEditor):
    def __init__(self, *, minimum: int = 0, maximum: int = 10_000_000) -> None:
        super().__init__()
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spin)
        self.spin.valueChanged.connect(self.value_changed.emit)

    def value(self) -> int:
        return self.spin.value()

    def set_value(self, value: int) -> None:
        self.spin.setValue(int(value or 0))


class FloatEditor(FieldEditor):
    def __init__(
        self,
        *,
        minimum: float = 0.0,
        maximum: float = 10_000.0,
        step: float = 0.01,
    ) -> None:
        super().__init__()
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(4)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spin)

        self.spin.valueChanged.connect(self.value_changed.emit)

    def value(self) -> float:
        return self.spin.value()

    def set_value(self, value: float) -> None:
        self.spin.setValue(float(value or 0.0))


class ColorEditor(FieldEditor):
    def __init__(self) -> None:
        super().__init__()
        self.edit = QLineEdit()
        self.button = QPushButton("Pick")
        self.button.setFixedWidth(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit)
        layout.addWidget(self.button)

        self.edit.textChanged.connect(lambda value: self.value_changed.emit(value))
        self.button.clicked.connect(self._pick_color)

    def value(self) -> object:
        return self.edit.text()

    def set_value(self, value: str) -> None:
        if value is None:
            self.edit.clear()
        else:
            self.edit.setText(value)
            text_color = text_color_for_background(value)
            self.button.setStyleSheet(f"background-color: {value}; color: {text_color}")

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.edit.text()), self)
        if color.isValid():
            self.set_value(color.name())


def text_color_for_background(color: str) -> str:
    """
    Return '#000000' or '#ffffff' for readable text on the given background.

    Accepts:
        '#RGB'
        '#RRGGBB'
        'RGB'
        'RRGGBB'
    """
    hex_color = color.strip().lstrip("#")

    if len(hex_color) == 3:
        hex_color = "".join(ch * 2 for ch in hex_color)

    if len(hex_color) != 6:
        raise ValueError(f"Expected a hex color like '#RRGGBB', got {color!r}")

    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)

    def linearize(channel: int) -> float:
        value = channel / 255.0
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    luminance = (
        0.2126 * linearize(red)
        + 0.7152 * linearize(green)
        + 0.0722 * linearize(blue)
    )

    return "#000000" if luminance > 0.179 else "#ffffff"



class Point2Editor(FieldEditor):
    def __init__(
        self,
        *,
        minimum: float = 0.0,
        maximum: float = 1.0,
        step: float = 0.01,
    ) -> None:
        super().__init__()

        self.x_spin = QDoubleSpinBox()
        self.y_spin = QDoubleSpinBox()

        for spin in (self.x_spin, self.y_spin):
            spin.setRange(minimum, maximum)
            spin.setSingleStep(step)
            spin.setDecimals(4)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.x_spin)
        layout.addWidget(self.y_spin)

        self.x_spin.valueChanged.connect(lambda _: self.value_changed.emit(self.value()))
        self.y_spin.valueChanged.connect(lambda _: self.value_changed.emit(self.value()))

    def value(self) -> object:
        return [self.x_spin.value(), self.y_spin.value()]

    def set_value(self, value: object) -> None:
        if isinstance(value, list | tuple) and len(value) >= 2:
            self.x_spin.setValue(float(value[0]))
            self.y_spin.setValue(float(value[1]))
        else:
            self.x_spin.setValue(0.0)
            self.y_spin.setValue(0.0)


class LayerTypeEditor(FieldEditor):
    def __init__(self) -> None:
        super().__init__()
        self.combo = QComboBox()
        self.combo.addItems([item.value for item in LightLayerType])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.combo)

        self.combo.currentTextChanged.connect(
            lambda value: self.value_changed.emit(LightLayerType(value))
        )

    def value(self) -> object:
        return LightLayerType(self.combo.currentText())

    def set_value(self, value: object) -> None:
        if isinstance(value, LightLayerType):
            self.combo.setCurrentText(value.value)
        else:
            self.combo.setCurrentText(str(value))


class BoolEditor(FieldEditor):
    value_changed = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.checkbox = QCheckBox()
        self.checkbox.toggled.connect(self.value_changed.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox)

    def value(self) -> bool:
        return self.checkbox.isChecked()

    def set_value(self, value: Any) -> None:
        self.checkbox.setChecked(bool(value))


EditorFactory = Callable[[Field[Any]], FieldEditor]


class FieldEditorRegistry:
    def __init__(self) -> None:
        self._by_editor_name: dict[str, EditorFactory] = {}

    def register(self, editor_name: str, factory: EditorFactory) -> None:
        self._by_editor_name[editor_name] = factory

    def create_editor(self, field_def: Field[Any]) -> FieldEditor:
        editor_name = str(field_def.metadata.get("editor", "text"))

        factory = self._by_editor_name.get(editor_name)
        if factory is None:
            factory = self._by_editor_name["text"]

        return factory(field_def)


def default_field_editor_registry() -> FieldEditorRegistry:
    registry = FieldEditorRegistry()

    registry.register("text", lambda field_def: TextEditor())

    registry.register(
        "int",
        lambda field_def: IntEditor(
            minimum=int(field_def.metadata.get("min", 0)),
            maximum=int(field_def.metadata.get("max", 10_000_000)),
        ),
    )

    registry.register(
        "float",
        lambda field_def: FloatEditor(
            minimum=float(field_def.metadata.get("min", 0.0)),
            maximum=float(field_def.metadata.get("max", 10_000.0)),
            step=float(field_def.metadata.get("step", 0.01)),
        ),
    )

    registry.register("color", lambda field_def: ColorEditor())

    registry.register(
        "point2",
        lambda field_def: Point2Editor(
            minimum=float(field_def.metadata.get("min", 0.0)),
            maximum=float(field_def.metadata.get("max", 1.0)),
            step=float(field_def.metadata.get("step", 0.01)),
        ),
    )

    registry.register("layer_type", lambda field_def: LayerTypeEditor())

    registry.register("bool", lambda field_def: BoolEditor())

    return registry