from .qt_audio_backend import QtAudioBackend
from .portaudio_backend import PortAudioBackend
from .portaudio_player import PortAudioMixerPlayer


PortAudioBackend.set_default_player(PortAudioMixerPlayer())


__all__ = ["QtAudioBackend", "PortAudioBackend"]
