from dataclasses import asdict, fields, is_dataclass
from typing import Any, get_args, get_origin, get_type_hints

import yaml

try:  # pragma: no cover - exercised when mashumaro is installed
    from mashumaro.mixins.yaml import DataClassYAMLMixin as _MashumaroMixin
except Exception:  # noqa: BLE001
    _MashumaroMixin = None


class _FallbackDataClassYAMLMixin:
    @classmethod
    def from_yaml(cls, data: str):
        raw = yaml.safe_load(data)
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Any):
        return _coerce_value(cls, raw)

    def to_yaml(self) -> str:
        return yaml.safe_dump(asdict(self), sort_keys=False)


def _coerce_value(annotation: Any, value: Any):
    origin = get_origin(annotation)
    if value is None:
        return None

    if origin is list:
        (inner_type,) = get_args(annotation)
        return [_coerce_value(inner_type, item) for item in value]

    if origin is dict:
        key_type, value_type = get_args(annotation)
        return {
            _coerce_value(key_type, k): _coerce_value(value_type, v)
            for k, v in value.items()
        }

    if origin is tuple:
        inner = get_args(annotation)
        if len(inner) == 2 and inner[1] is Ellipsis:
            return tuple(_coerce_value(inner[0], item) for item in value)
        return tuple(_coerce_value(t, item) for t, item in zip(inner, value, strict=False))

    if origin is not None and type(None) in get_args(annotation):
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)][0]
        return _coerce_value(non_none, value)

    if isinstance(annotation, type) and is_dataclass(annotation):
        hints = get_type_hints(annotation)
        kwargs = {}
        for field in fields(annotation):
            if field.name in value:
                kwargs[field.name] = _coerce_value(hints.get(field.name, field.type), value[field.name])
        return annotation(**kwargs)

    return value


DataClassYAMLMixin = _MashumaroMixin or _FallbackDataClassYAMLMixin
