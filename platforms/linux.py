"""Linux platform backend for E-SHELL.

Linux-specific operations are introduced in later commits. Until then, this
backend fulfills the shared contract and reports unimplemented operations
consistently.

gist: 
    The main file. in which almost entire Linux-Specific 
    after init. we have this Backend called by Handler. 
"""

from platforms.base import PlatformBackend
from platforms.errors import UnsupportedOperationError
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess


class LinuxBackend(PlatformBackend):
    """Linux backend placeholder until operations migrate from commands.py."""

    def supports(self, capability: str) -> bool:
        """Return False until the corresponding Linux operation is implemented."""
        return False

    # --- System Information ---

    def get_gpu_info(self) -> str:
        raise UnsupportedOperationError("get_gpu_info", "linux")

    def get_battery_info(self) -> str:
        raise UnsupportedOperationError("get_battery_info", "linux")

    def get_disk_usage(self) -> str:
        raise UnsupportedOperationError("get_disk_usage", "linux")

    def get_memory_usage(self) -> str:
        raise UnsupportedOperationError("get_memory_usage", "linux")

    def get_system_uptime(self) -> str:
        raise UnsupportedOperationError("get_system_uptime", "linux")

    def get_kernel_info(self) -> str:
        raise UnsupportedOperationError("get_kernel_info", "linux")

    def get_cpu_info(self) -> str:
        raise UnsupportedOperationError("get_cpu_info", "llinux")

    def get_current_user(self) -> str:
        raise UnsupportedOperationError("get_current_user", "linux")

    def get_hostname(self) -> str:
        raise UnsupportedOperationError("get_hostname", "linux")

    def get_os_info(self) -> str:
        raise UnsupportedOperationError("get_os_info", "linux")

    def get_network_info(self) -> str:
        raise UnsupportedOperationError("get_network_info", "linux")

    def get_logged_in_users(self) -> str:
        raise UnsupportedOperationError("get_logged_in_users", "linux")

    def get_running_processes(self) -> str:
        raise UnsupportedOperationError("get_running_processes", "linux")

    def get_environment_info(self) -> Dict[str, str]:
        raise UnsupportedOperationError("get_environment_info", "linux")

    def get_python_version(self) -> str:
        raise UnsupportedOperationError("get_python_version", "linux")

    def get_package_manager_info(self) -> str:
        raise UnsupportedOperationError("get_package_manager_info", "linux")

    def get_fastfetch_info(self) -> str:
        raise UnsupportedOperationError("get_fastfetch_info", "linux")

    # --- File Operations ---

    def create_file(self, path: Path) -> bool:
        raise UnsupportedOperationError("create_file", "linux")

    def create_directory(self, path: Path) -> bool:
        raise UnsupportedOperationError("create_directory", "linux")

    def copy_file(self, source: Path, destination: Path) -> bool:
        raise UnsupportedOperationError("copy_file", "linux")

    def make_executable(self, path: Path) -> bool:
        raise UnsupportedOperationError("make_executable", "linux")

    def edit_file(self, path: Path, editor: str) -> bool:
        raise UnsupportedOperationError("edit_file", "linux")

    def run_file(self, path: Path) -> bool:
        raise UnsupportedOperationError("run_file", "linux")

    def extract_zip(self, archive_path: Path, extract_to: Path) -> int:
        raise UnsupportedOperationError("extract_zip", "linux")

    # --- Process Execution ---

    def run_command(self, args: List[str], cwd: Optional[Path] = None) -> Optional[subprocess.CompletedProcess]:
        raise UnsupportedOperationError("run_command", "linux")

    def launch_background(self, args: List[str]) -> bool:
        raise UnsupportedOperationError("launch_background", "linux")

    def run_and_capture(self, args: List[str], cwd: Optional[Path] = None, timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        raise UnsupportedOperationError("run_and_capture", "linux")

    # --- Platform Capabilities ---

    def has_display(self) -> bool:
        raise UnsupportedOperationError("has_display", "linux")

    def which(self, command: str) -> Optional[str]:
        raise UnsupportedOperationError("which", "linux")

    def get_shell(self) -> str:
        raise UnsupportedOperationError("get_shell", "linux")

    def get_editor_command(self, editor_name: str) -> Optional[List[str]]:
        raise UnsupportedOperationError("get_editor_command", "linux")

    def is_editor_gui(self, editor_name: str) -> bool:
        raise UnsupportedOperationError("is_editor_gui", "linux")

    def get_supported_editors(self) -> Dict[str, Dict[str, Any]]:
        raise UnsupportedOperationError("get_supported_editors", "linux")

    # --- Utility ---

    def get_workspace_dir(self) -> Path:
        raise UnsupportedOperationError("get_workspace_dir", "linux")

    def get_project_dir(self) -> Path:
        raise UnsupportedOperationError("get_project_dir", "linux")

    def validate_filename(self, name: str) -> bool:
        raise UnsupportedOperationError("validate_filename", "linux")

    def get_safe_path(self, filename: str) -> Optional[Path]:
        raise UnsupportedOperationError("get_safe_path", "linux")

    def safe_name(self, name: str, label: str) -> Optional[Path]:
        raise UnsupportedOperationError("safe_name", "linux")
