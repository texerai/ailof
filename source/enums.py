# Copyright (c) 2024 texer.ai. All rights reserved.
import enum


class Command(enum.Enum):
    UNDEFINED = 0
    UP = 1
    DOWN = 2
    TERMINATE = 3
    SELECT = 4
    SEARCH = 5
    CONTINUE = 6


class ReturnCode(enum.Enum):
    SUCCESS = 0
    FAILURE = 1
    TERMINATE = 2
