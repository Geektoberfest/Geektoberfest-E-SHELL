"""Linux platform backend for E-SHELL.

Linux-specific operations are introduced in later commits. Until then, this
backend fulfills the shared contract and reports unimplemented operations
consistently.

gist: 
    The main file. in which almost entire Linux-Specific 
    after init. we have this Backend called by Handler. 
"""

import getpass
import os
import platform
import shutil
import socket
import sys
from platforms.base import PlatformBackend
from platforms.errors import UnsupportedOperationError
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess


class LinuxBackend(PlatformBackend):

    def supports(self, capability: str) -> bool:
        """Return capabilities implemented by this backend."""
        return capability in {"system_info", "process_execution"}

    @staticmethod
    def _capture(args: List[str]) -> Optional[str]:
        """Run a known-safe command and return its standard output."""
        try:
            result = subprocess.run(args, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return None
        return result.stdout.rstrip()

    # --- System Information ---

    def get_gpu_info(self) -> str:
        output = self._capture(["lspci"])
        if output is None:
            return "lspci is not installed, so GPU information is unavailable."
        gpu_lines = [
            line
            for line in output.splitlines()
            if any(word in line.lower() for word in ("vga", "3d", "display"))
        ]
        return "\n".join(gpu_lines) if gpu_lines else "No GPU entry found."

    def get_battery_info(self) -> str:
        batteries = sorted(Path("/sys/class/power_supply").glob("BAT*"))
        if not batteries:
            return "No battery information found."

        details = []
        for battery in batteries:
            capacity = battery / "capacity"
            status = battery / "status"
            capacity_text = capacity.read_text().strip() if capacity.exists() else "unknown"
            status_text = status.read_text().strip() if status.exists() else "unknown"
            details.append(f"{battery.name}: {capacity_text}% ({status_text})")
        return "\n".join(details)

    def get_disk_usage(self) -> str:
        output = self._capture(["df", "-h"])
        if output is not None:
            return output
        try:
            usage = shutil.disk_usage("/")
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            return (
                f"Root filesystem (fallback): {used_gb:.1f}G used, {free_gb:.1f}G free, "
                f"{total_gb:.1f}G total (df not installed)"
            )
        except OSError:
            return " Disk usage information is unavailable (df is not installed)."

    def get_memory_usage(self) -> str:
        output = self._capture(["free", "-h"])
        if output is not None:
            return output

        meminfo = Path("/proc/meminfo")
        if meminfo.is_file():
            try:
                memory = dict(line.split(":", 1) for line in meminfo.read_text().splitlines() if ":" in line)
                total = memory.get("MemTotal", "").strip()
                available = memory.get("MemAvailable", memory.get("MemFree", "")).strip()
                if total and available:
                    return (
                        "Memory (fallback from /proc/meminfo): "
                        f"Total: {total}, Available: {available} (free not installed)"
                    )
            except OSError:
                pass
        return " Memory usage information is unavailable (free is not installed)."

    def get_system_uptime(self) -> str:
        output = self._capture(["uptime"])
        if output is not None:
            return output

        uptime_file = Path("/proc/uptime")
        try:
            total_seconds = float(uptime_file.read_text().split()[0])
            hours, remainder = divmod(int(total_seconds), 3600)
            minutes, _ = divmod(remainder, 60)
            days, hours = divmod(hours, 24)
            if days:
                return f"System uptime (fallback): {days} day(s), {hours} hour(s), {minutes} minute(s)"
            return f"System uptime (fallback): {hours} hour(s), {minutes} minute(s)"
        except (ValueError, OSError, IndexError):
            return "System uptime is unavailable (uptime not installed)."

    def get_kernel_info(self) -> str:
        output = self._capture(["uname", "-a"])
        return output if output is not None else f"Kernel info (fallback): {platform.platform()}"

    def get_cpu_info(self) -> str:
        output = self._capture(["lscpu"])
        if output is not None:
            return output

        cpuinfo = Path("/proc/cpuinfo")
        try:
            model_lines = [
                line.split(":", 1)[1].strip()
                for line in cpuinfo.read_text().splitlines()
                if line.startswith("model name")
            ]
            if model_lines:
                return (
                    f"CPU (fallback from /proc/cpuinfo): {model_lines[0]} "
                    f"({len(model_lines)} core(s)) (lscpu not installed)"
                )
        except OSError:
            pass
        return " CPU information is unavailable (lscpu is not installed)."

    def get_current_user(self) -> str:
        output = self._capture(["whoami"])
        if output is not None:
            return output
        try:
            return getpass.getuser()
        except OSError:
            return os.environ.get("USER") or os.environ.get("LOGNAME") or " Current user information is unavailable."

    def get_hostname(self) -> str:
        output = self._capture(["hostname"])
        if output is not None:
            return output
        try:
            return socket.gethostname()
        except OSError:
            return " Hostname is unavailable."

    def get_os_info(self) -> str:
        output = self._capture(["lsb_release", "-a"])
        if output is not None:
            return output
        try:
            return Path("/etc/os-release").read_text().strip()
        except OSError:
            output = self._capture(["uname", "-sro"])
            return output if output is not None else " OS distribution information is unavailable."

    def get_network_info(self) -> str:
        output = self._capture(["ip", "addr", "show"])
        if output is None:
            output = self._capture(["ifconfig"])
        if output is not None:
            return output
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return f"Network info (fallback): Host: {hostname}, IP: {ip} (ip/ifconfig not available)"
        except OSError:
            return " Network information is unavailable (ip and ifconfig not installed)."

    def get_logged_in_users(self) -> str:
        output = self._capture(["who"])
        if output is None:
            output = self._capture(["w"])
        if output is not None:
            return output
        user = os.environ.get("USER")
        if user:
            return f"Logged in user (fallback): {user}"
        return " Logged in users information is unavailable (who is not installed)."

    def get_running_processes(self) -> str:
        output = self._capture(["ps", "aux", "--sort=-%mem"])
        if output is None:
            return " ps is not installed, so running processes information is unavailable."
        # header plus the 10 largest processes
        return "\n".join(output.splitlines()[:11])

    def get_environment_info(self) -> Dict[str, str]:
        return {key: os.environ.get(key, "") for key in ("USER", "HOME", "SHELL", "LANG", "TERM", "PATH")}

    def get_python_version(self) -> str:
        output = self._capture(["python3", "--version"])
        return output if output is not None else f"Python {sys.version.split()[0]} (internal)"

    def get_package_manager_info(self) -> str:
        managers = ("apt", "dnf", "pacman", "zypper", "apk")
        found = [manager for manager in managers if shutil.which(manager)]
        return "Detected package manager(s): " + ", ".join(found) if found else "No common package manager detected."

    def get_fastfetch_info(self) -> str:
        output = self._capture(["fastfetch"])
        if output is not None:
            return output

        sections = ["fastfetch is not installed. Showing safe fallback system information instead."]
        for command in (["uname", "-a"], ["lscpu"], ["free", "-h"], ["df", "-h"]):
            sections.append(f"$ {' '.join(command)}")
            sections.append(self._capture(command) or f" Command not available: {command[0]}")
        return "\n\n".join(sections)

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
        """Run a known-safe command without invoking a shell."""
        try:
            return subprocess.run(args, cwd=cwd, check=False)
        except FileNotFoundError:
            print(f" Command not available: {args[0]}")
            return None

    def launch_background(self, args: List[str]) -> bool:
        """Start a known GUI program without using a shell."""
        try:
            subprocess.Popen(args)
        except FileNotFoundError:
            print(f" Command not available: {args[0]}")
            return False
        return True

    def run_and_capture(self, args: List[str], cwd: Optional[Path] = None, timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        raise UnsupportedOperationError("run_and_capture", "linux")

    # --- Platform Capabilities ---

    def has_display(self) -> bool:
        raise UnsupportedOperationError("has_display", "linux")

    def which(self, command: str) -> Optional[str]:
        raise UnsupportedOperationError("which", "linux")

    def get_shell(self) -> str:
        return os.environ.get("SHELL", "Unknown shell")

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
