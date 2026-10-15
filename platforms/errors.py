"""Platform capability errors for E-SHELL.

Defines exceptions raised when a platform backend doesn't support
a requested operation or capability.

gist: 
    PlatformError ( exception class ) 
    to have exceptions specifying custom logic
    -UnsupportedOperation -> that specific OS doesn't support the operation 
    -CapabilityNotAvailable -> that specific OS doesn't have certain capability/tooling to use 
                                e.g. ssh-ed Linux won't have Display
    -CommandNotFound -> Command handles aren't present for that OS backend
    -PlatformDetection -> for some reason runtime flag can't detect the OS backend
    -BackendNotImplemented -> tha backend is not written for that specific OS.

    Pretty necessary exceptions.

"""


class PlatformError(Exception):
    """Base exception for platform-related errors."""
    pass


class UnsupportedOperationError(PlatformError):
    """Raised when a platform backend doesn't support a requested operation."""

    def __init__(self, operation: str, platform: str = None):
        self.operation = operation
        self.platform = platform
        platform_info = f" on {platform}" if platform else ""
        super().__init__(f"Operation '{operation}' is not supported{platform_info}")


class CapabilityNotAvailableError(PlatformError):
    """Raised when a platform capability is not available (e.g., no display, no battery)."""

    def __init__(self, capability: str, platform: str = None, reason: str = None):
        self.capability = capability
        self.platform = platform
        self.reason = reason
        platform_info = f" on {platform}" if platform else ""
        reason_info = f": {reason}" if reason else ""
        super().__init__(f"Capability '{capability}' is not available{platform_info}{reason_info}")


class CommandNotFoundError(PlatformError):
    """Raised when a required command/executable is not found on the platform."""

    def __init__(self, command: str, platform: str = None):
        self.command = command
        self.platform = platform
        platform_info = f" on {platform}" if platform else ""
        super().__init__(f"Command '{command}' not found{platform_info}")


class PlatformDetectionError(PlatformError):
    """Raised when platform detection fails or returns unexpected results."""
    pass


class BackendNotImplementedError(PlatformError):
    """Raised when a platform backend has not been implemented yet."""

    def __init__(self, platform: str):
        self.platform = platform
        super().__init__(f"No backend implemented for platform: {platform}")
