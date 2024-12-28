# Copyright (c) 2024 texer.ai. All rights reserved.
class UserTerminationException(Exception):
    """Raised when user requests program termination (e.g., via Ctrl+C)"""

    pass
