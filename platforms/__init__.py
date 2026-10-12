"""Platform abstraction package for E-SHELL.

This package provides platform-specific backends for system operations,
allowing the command routing layer to remain platform-agnostic.
"""

from platforms.base import (
    PlatformBackend,
    get_platform_name,
    is_linux,
    is_windows,
    is_macos,
)
from platforms.errors import (
    PlatformError,
    UnsupportedOperationError,
    CapabilityNotAvailableError,
    CommandNotFoundError,
    PlatformDetectionError,
    BackendNotImplementedError,
)

__all__ = [
    "PlatformBackend",
    "get_platform_name",
    "is_linux",
    "is_windows",
    "is_macos",
    "PlatformError",
    "UnsupportedOperationError",
    "CapabilityNotAvailableError",
    "CommandNotFoundError",
    "PlatformDetectionError",
    "BackendNotImplementedError",
]