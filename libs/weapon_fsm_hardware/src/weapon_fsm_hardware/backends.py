import abc


class AudioBackend(abc.ABC):
    @abc.abstractmethod
    def play_audio(
        self,
        *,
        clip: str,
        path: str,
        mode: str,
        interrupt: str,
    ) -> None: ...

    @abc.abstractmethod
    def stop_audio(self) -> None: ...


class LightBackend(abc.ABC):
    @abc.abstractmethod
    def play_light(
        self,
        *,
        sequence: str,
        path: str,
        mode: str,
    ) -> None: ...

    @abc.abstractmethod
    def stop_light(self) -> None: ...
