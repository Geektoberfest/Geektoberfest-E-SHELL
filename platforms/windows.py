"""Windows platform backend for E-SHELL.

Windows operations are implemented in later commits. This backend establishes
the shared contract and reports unsupported operations consistently.

gist:
    Master file for Windows BAckend and FUnctions
    This will have Python + Powershell. as we will try not to break
    cross platform dependencies.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from platforms.base import PlatformBackend
from platforms.errors import UnsupportedOperationError


class WindowsBackend(PlatformBackend):
    """Windows backend scaffold."""

    def _unsupported(self, operation: str):
        raise UnsupportedOperationError(operation, "windows")

    def supports(self, capability: str) -> bool:
        return False

    # --- System Information ---

    def get_gpu_info(self) -> str:
        return self._unsupported("get_gpu_info")

    def get_battery_info(self) -> str:
        return self._unsupported("get_battery_info")

    def get_disk_usage(self) -> str:
        return self._unsupported("get_disk_usage")

    def get_memory_usage(self) -> str:
        return self._unsupported("get_memory_usage")

    def get_system_uptime(self) -> str:
        return self._unsupported("get_system_uptime")

    def get_kernel_info(self) -> str:
        return self._unsupported("get_kernel_info")

    def get_cpu_info(self) -> str:
        return self._unsupported("get_cpu_info")

    def get_current_user(self) -> str:
        return self._unsupported("get_current_user")

    def get_hostname(self) -> str:
        return self._unsupported("get_hostname")

    def get_os_info(self) -> str:
        return self._unsupported("get_os_info")

    def get_network_info(self) -> str:
        return self._unsupported("get_network_info")

    def get_logged_in_users(self) -> str:
        return self._unsupported("get_logged_in_users")

    def get_running_processes(self) -> str:
        return self._unsupported("get_running_processes")

    def get_environment_info(self) -> Dict[str, str]:
        return self._unsupported("get_environment_info")

    def get_python_version(self) -> str:
        return self._unsupported("get_python_version")

    def get_package_manager_info(self) -> str:
        return self._unsupported("get_package_manager_info")

    def get_fastfetch_info(self) -> str:
        return self._unsupported("get_fastfetch_info")

    # --- File Operations ---

    def create_file(self, path: Path) -> bool:
        return self._unsupported("create_file")

    def create_directory(self, path: Path) -> bool:
        return self._unsupported("create_directory")

    def copy_file(self, source: Path, destination: Path) -> bool:
        return self._unsupported("copy_file")

    def make_executable(self, path: Path) -> bool:
        return self._unsupported("make_executable")

    def edit_file(self, path: Path, editor: str) -> bool:
        return self._unsupported("edit_file")

    def run_file(self, path: Path) -> bool:
        return self._unsupported("run_file")

    def extract_zip(self, archive_path: Path, extract_to: Path) -> int:
        return self._unsupported("extract_zip")

    # --- Process Execution ---

    def run_command(
        self, args: List[str], cwd: Optional[Path] = None
    ) -> Optional[subprocess.CompletedProcess]:
        return self._unsupported("run_command")

    def launch_background(self, args: List[str]) -> bool:
        return self._unsupported("launch_background")

    def run_and_capture(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        timeout: int = 10,
    ) -> Optional[subprocess.CompletedProcess]:
        return self._unsupported("run_and_capture")

    # --- Platform Capabilities ---

    def has_display(self) -> bool:
        return self._unsupported("has_display")

    def which(self, command: str) -> Optional[str]:
        return self._unsupported("which")

    def get_shell(self) -> str:
        return self._unsupported("get_shell")

    def get_editor_command(self, editor_name: str) -> Optional[List[str]]:
        return self._unsupported("get_editor_command")

    def is_editor_gui(self, editor_name: str) -> bool:
        return self._unsupported("is_editor_gui")

    def get_supported_editors(self) -> Dict[str, Dict[str, Any]]:
        return self._unsupported("get_supported_editors")

    # --- Utility ---

    def get_workspace_dir(self) -> Path:
        return self._unsupported("get_workspace_dir")

    def get_project_dir(self) -> Path:
        return self._unsupported("get_project_dir")

    def validate_filename(self, name: str) -> bool:
        return self._unsupported("validate_filename")

    def get_safe_path(self, filename: str) -> Optional[Path]:
        return self._unsupported("get_safe_path")

    def safe_name(self, name: str, label: str) -> Optional[Path]:
        return self._unsupported("safe_name")
