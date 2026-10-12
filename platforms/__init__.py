"""Platform abstraction and backend selection for E-SHELL.

This package provides platform-specific backends for system operations,
allowing the command routing layer to remain platform-agnostic.

gist:
uses Abstract Base Class and it's Abstract methods so we can make linux.
get_gpu_info()
like code.
It has abstracted layers as it will be easier for routing phrases.
as we do not have an internal language
or we are not resolving Cmds with Syntax tree with parser
or we are not using whole Argument resolution
"""

import platform

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

### select of the Backend based on OS. 
def get_backend() -> PlatformBackend:
    """Return a new backend for the current operating system."""
    os_name = platform.system()

    if os_name == "Linux":
        from platforms.linux import LinuxBackend

        return LinuxBackend()
    elif os_name == "Windows":
        from platforms.windows import WindowsBackend

        return WindowsBackend()
    elif os_name == "Darwin":
        from platforms.macos import MacOSBackend

        return MacOSBackend()
    else:
        raise BackendNotImplementedError(os_name)


# all the necessary imports in __all__
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
    "get_backend",
]
