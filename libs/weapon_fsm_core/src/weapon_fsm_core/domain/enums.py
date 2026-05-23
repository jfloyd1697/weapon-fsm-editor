from enum import StrEnum


class AudioMode(StrEnum):
    ONCE = "once"
    LOOP = "loop"


class AudioInterrupt(StrEnum):
    IGNORE = "ignore"
    SCHEDULE = "schedule"
    INTERRUPT = "interrupt"
    INTERRUPT_ALL = "interrupt_all"
    OVERLAP = "overlap"


class ClipSetMode(StrEnum):
    RANDOM = "random"
    RANDOM_NO_REPEAT = "random_no_repeat"
    SEQUENCE = "sequence"


class LightMode(StrEnum):
    ONCE = "once"
    LOOP = "loop"
