# Copyright (c) 2024 texer.ai. All rights reserved.
import enum


class Command(enum.Enum):
    UNDEFINED = 0
    UP = 1
    DOWN = 2
    TERMINATE = 3
    SELECT_AND_GATE = 4
    SELECT_OR_GATE = 5
    SELECT = 6
    SEARCH = 7
    CONTINUE = 8


class ReturnCode(enum.Enum):
    SUCCESS = 0
    FAILURE = 1
    TERMINATE = 2
