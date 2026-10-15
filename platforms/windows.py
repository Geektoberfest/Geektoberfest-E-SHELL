"""Windows platform backend for E-SHELL.

Windows operations are implemented in later commits. This backend establishes
the shared contract and reports unsupported operations consistently.

gist:
    Master file for Windows BAckend and FUnctions
    This will have Python + Powershell. as we will try not to break
    cross platform dependencies.
"""

import ctypes
import getpass
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional

from platforms.base import PlatformBackend
from platforms.errors import UnsupportedOperationError


class WindowsBackend(PlatformBackend):
    """Windows backend scaffold."""

    def _unsupported(self, operation: str) -> NoReturn:
        raise UnsupportedOperationError(operation, "windows")

    def supports(self, capability: str) -> bool:
        return capability == "system_info"

    # --- System Information ---

    def get_gpu_info(self) -> str:
        return self._unsupported("get_gpu_info")

    def get_battery_info(self) -> str:
        return self._unsupported("get_battery_info")

    def get_disk_usage(self) -> str:
        drive = os.environ.get("SystemDrive") or Path.home().anchor or "C:\\"
        try:
            usage = shutil.disk_usage(drive)
        except OSError:
            return "Disk usage information is unavailable."

        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        return f"{drive} {used_gb:.1f}G used, {free_gb:.1f}G free, {total_gb:.1f}G total"

    def get_memory_usage(self) -> str:
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        try:
            succeeded = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        except (AttributeError, OSError):
            return "Memory usage information is unavailable."
        if not succeeded:
            return "Memory usage information is unavailable."

        total_gb = status.total_physical / (1024 ** 3)
        available_gb = status.available_physical / (1024 ** 3)
        used_gb = total_gb - available_gb
        return (
            f"Memory: {used_gb:.1f}G used, {available_gb:.1f}G available, "
            f"{total_gb:.1f}G total ({status.memory_load}% load)"
        )

    def get_system_uptime(self) -> str:
        try:
            total_seconds = ctypes.windll.kernel32.GetTickCount64() // 1000
        except (AttributeError, OSError):
            return "System uptime is unavailable."

        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days:
            return f"System uptime: {days} day(s), {hours} hour(s), {minutes} minute(s)"
        return f"System uptime: {hours} hour(s), {minutes} minute(s)"

    def get_kernel_info(self) -> str:
        return f"Windows {platform.release()} ({platform.version()})"

    def get_cpu_info(self) -> str:
        processor = os.environ.get("PROCESSOR_IDENTIFIER") or platform.processor()
        if not processor:
            return "CPU information is unavailable."
        cores = os.cpu_count()
        return f"CPU: {processor}" + (f" ({cores} logical processor(s))" if cores else "")

    def get_current_user(self) -> str:
        try:
            return getpass.getuser()
        except OSError:
            return os.environ.get("USERNAME") or "Current user information is unavailable."

    def get_hostname(self) -> str:
        try:
            return socket.gethostname()
        except OSError:
            return "Hostname is unavailable."

    def get_os_info(self) -> str:
        return platform.platform()

    def get_network_info(self) -> str:
        try:
            hostname = socket.gethostname()
            addresses = sorted(
                {
                    address[4][0]
                    for address in socket.getaddrinfo(hostname, None)
                    if address[0] in (socket.AF_INET, socket.AF_INET6)
                }
            )
        except OSError:
            return "Network information is unavailable."

        address_text = ", ".join(addresses) if addresses else "unavailable"
        return f"Host: {hostname}\nIP address(es): {address_text}"

    def get_logged_in_users(self) -> str:
        return self._unsupported("get_logged_in_users")

    def get_running_processes(self) -> str:
        return self._unsupported("get_running_processes")

    def get_environment_info(self) -> Dict[str, str]:
        keys = ("USERNAME", "USERPROFILE", "COMSPEC", "LANG", "TERM", "PATH")
        return {key: os.environ.get(key, "") for key in keys}

    def get_python_version(self) -> str:
        return f"Python {sys.version.split()[0]} ({sys.executable})"

    def get_package_manager_info(self) -> str:
        managers = ("winget", "choco", "scoop")
        found = [manager for manager in managers if shutil.which(manager)]
        if not found:
            return "No common package manager detected."
        return "Detected package manager(s): " + ", ".join(found)

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
