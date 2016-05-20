from enum import Enum


class PlayState(Enum):
    Playing = 1
    Paused = 2
    SeekBack = 3
    SeekForward = 4
    NotReady = 5
    EndOfStream = 6
