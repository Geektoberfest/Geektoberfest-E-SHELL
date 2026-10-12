"""Platform abstraction package for E-SHELL.

This package provides platform-specific backends for system operations,
allowing the command routing layer to remain platform-agnostic.

gist: 
    first entry point after commands routes the control flow here
    initializing and importing all platform-backend:q:q interface related functions
"""

from platforms.base import (
    PlatformBackend,
    get_platform_name, 
    is_linux,
    is_windows,
    is_macos,
)

# to easily import all stuff
__all__ = [
    "PlatformBackend",
    "get_platform_name",
    "is_linux",
    "is_windows",
    "is_macos",
]
