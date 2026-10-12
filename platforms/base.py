"""Platform backend contract for E-SHELL.

This module defines the abstract base class that all platform backends must implement *on* (imp to mention yk).
It separates OS-specific operations from command routing logic.

gist: 
    uses Abstract Base Class and it's Abstract methods so we can make linux.get_gpu_info()
    like code. 
    It has abstracted layers as it will be easier for routing phrases.
    as we do not have an internal language 
    or we are not resolving Cmds with Syntax tree with parser
    or we are not using whole Argument resolution
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess


class PlatformBackend(ABC):
    """Abstract base class for platform-specific operations.

    All platform backends (Linux, Windows, etc.) must implement this interface.
    The command routing layer uses this interface without knowing the concrete platform.
    """

    # --- System Information ---

    @abstractmethod
    def get_gpu_info(self) -> str:
        """Return GPU information as a formatted string."""
        ...

    @abstractmethod
    def get_battery_info(self) -> str:
        """Return battery information as a formatted string."""
        ...

    @abstractmethod
    def get_disk_usage(self) -> str:
        """Return disk usage information as a formatted string."""
        ...

    @abstractmethod
    def get_memory_usage(self) -> str:
        """Return memory usage information as a formatted string."""
        ...

    @abstractmethod
    def get_system_uptime(self) -> str:
        """Return system uptime as a formatted string."""
        ...

    @abstractmethod
    def get_kernel_info(self) -> str:
        """Return kernel information as a formatted string."""
        ...

    @abstractmethod
    def get_cpu_info(self) -> str:
        """Return CPU information as a formatted string."""
        ...

    @abstractmethod
    def get_current_user(self) -> str:
        """Return current username as a string."""
        ...

    @abstractmethod
    def get_hostname(self) -> str:
        """Return system hostname as a string."""
        ...

    @abstractmethod
    def get_os_info(self) -> str:
        """Return OS distribution information as a formatted string."""
        ...

    @abstractmethod
    def get_network_info(self) -> str:
        """Return network information as a formatted string."""
        ...

    @abstractmethod
    def get_logged_in_users(self) -> str:
        """Return logged-in users information as a formatted string."""
        ...

    @abstractmethod
    def get_running_processes(self) -> str:
        """Return running processes information as a formatted string."""
        ...

    @abstractmethod
    def get_environment_info(self) -> Dict[str, str]:
        """Return environment variables as a dictionary."""
        ...

    @abstractmethod
    def get_python_version(self) -> str:
        """Return Python version as a string."""
        ...

    @abstractmethod
    def get_package_manager_info(self) -> str:
        """Return detected package manager information as a string."""
        ...

    @abstractmethod
    def get_fastfetch_info(self) -> str:
        """Return fastfetch/system summary information as a string."""
        ...

    # --- File Operations ---

    @abstractmethod
    def create_file(self, path: Path) -> bool:
        """Create an empty file at the given path. Returns True on success."""
        ...

    @abstractmethod
    def create_directory(self, path: Path) -> bool:
        """Create a directory at the given path. Returns True on success."""
        ...

    @abstractmethod
    def copy_file(self, source: Path, destination: Path) -> bool:
        """Copy a file from source to destination. Returns True on success."""
        ...

    @abstractmethod
    def make_executable(self, path: Path) -> bool:
        """Make a file executable. Returns True on success."""
        ...

    @abstractmethod
    def edit_file(self, path: Path, editor: str) -> bool:
        """Open a file in the specified editor. Returns True on success."""
        ...

    @abstractmethod
    def run_file(self, path: Path) -> bool:
        """Run a file based on its extension. Returns True on success."""
        ...

    @abstractmethod
    def extract_zip(self, archive_path: Path, extract_to: Path) -> int:
        """Extract a ZIP archive. Returns number of files extracted."""
        ...

    # --- Process Execution ---

    @abstractmethod
    def run_command(self, args: List[str], cwd: Optional[Path] = None) -> Optional[subprocess.CompletedProcess]:
        """Run a command and return the completed process. Returns None if command not found."""
        ...

    @abstractmethod
    def launch_background(self, args: List[str]) -> bool:
        """Launch a GUI program in the background. Returns True on success."""
        ...

    @abstractmethod
    def run_and_capture(self, args: List[str], cwd: Optional[Path] = None, timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        """Run a command and capture output. Returns completed process or None on error/timeout."""
        ...

    # --- Platform Capabilities ---

    @abstractmethod
    def has_display(self) -> bool:
        """Check if a graphical display is available."""
        ...

    @abstractmethod
    def which(self, command: str) -> Optional[str]:
        """Return the path to an executable if found, else None."""
        ...

    @abstractmethod
    def get_shell(self) -> str:
        """Return the user's default shell."""
        ...

    @abstractmethod
    def get_editor_command(self, editor_name: str) -> Optional[List[str]]:
        """Return the command to launch an editor, or None if not supported."""
        ...

    @abstractmethod
    def is_editor_gui(self, editor_name: str) -> bool:
        """Check if an editor is GUI-based."""
        ...

    @abstractmethod
    def get_supported_editors(self) -> Dict[str, Dict[str, Any]]:
        """Return a dictionary of supported editors with their config."""
        ...

    # --- Utility ---

    @abstractmethod
    def get_workspace_dir(self) -> Path:
        """Return the workspace directory path."""
        ...

    @abstractmethod
    def get_project_dir(self) -> Path:
        """Return the project directory path."""
        ...

    @abstractmethod
    def validate_filename(self, name: str) -> bool:
        """Validate a filename for safety. Returns True if safe."""
        ...

    @abstractmethod
    def get_safe_path(self, filename: str) -> Optional[Path]:
        """Build a safe path inside workspace after validating filename."""
        ...

    @abstractmethod
    def safe_name(self, name: str, label: str) -> Optional[Path]:
        """Validate and resolve a name within the project directory."""
        ...


# --- Platform Detection ---

def get_platform_name() -> str:
    """Return the current platform name ('linux', 'windows', 'darwin', etc.)."""
    import platform
    return platform.system().lower()


def is_linux() -> bool:
    """Check if running on Linux."""
    return get_platform_name() == "linux"


def is_windows() -> bool:
    """Check if running on Windows."""
    return get_platform_name() == "windows"


def is_macos() -> bool:
    """Check if running on macOS."""
    return get_platform_name() == "darwin"


# soon to add more : D windows coming.
