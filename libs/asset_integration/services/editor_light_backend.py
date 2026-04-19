from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EditorLightBackend:
    loaded_paths: dict[str, str] = field(default_factory=dict)
    target_to_sequence: dict[str, str] = field(default_factory=dict)
    last_event: str | None = None

    def preload(self, sequence_name: str, path: str) -> None:
        self.loaded_paths[sequence_name] = str(Path(path))
        self.last_event = f"preload:{sequence_name}"

    def play(self, sequence_name: str, path: str, *, mode: str, target: str | None) -> None:
        self.loaded_paths.setdefault(sequence_name, str(Path(path)))
        if target is not None:
            self.target_to_sequence[target] = sequence_name
        self.last_event = f"play sequence={sequence_name} mode={mode} target={target}"

    def stop(self, *, sequence_name: str | None = None, target: str | None = None) -> None:
        if target is not None:
            self.target_to_sequence.pop(target, None)
        elif sequence_name is not None:
            to_remove = [name for name, current in self.target_to_sequence.items() if current == sequence_name]
            for name in to_remove:
                self.target_to_sequence.pop(name, None)
        else:
            self.target_to_sequence.clear()
        self.last_event = f"stop sequence={sequence_name} target={target}"

    def stop_all(self) -> None:
        self.target_to_sequence.clear()
        self.last_event = "stop_all"
