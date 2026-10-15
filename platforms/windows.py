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


EDITORS = {
    "notepad": {"command": ["notepad.exe"], "gui": True},
    "code": {"command": ["code"], "gui": True},
    "vscode": {"command": ["code"], "gui": True},
    "notepad++": {"command": ["notepad++.exe"], "gui": True},
    "sublime": {"command": ["subl"], "gui": True},
    "pycharm": {"command": ["pycharm64.exe"], "gui": True},
    "idle": {"command": ["idle"], "gui": True},
    "vim": {"command": ["vim"], "gui": False},
    "nvim": {"command": ["nvim"], "gui": False},
    "micro": {"command": ["micro"], "gui": False},
    "helix": {"command": ["hx"], "gui": False},
    "emacs": {"command": ["emacs", "-nw"], "gui": False},
}
RUN_TIMEOUT_SECONDS = 10
BLOCKED_NAME_PARTS = ("/", "\\", "..", "~", "*", "?", "&", "|", ";", "$", "`", ">", "<", ":")


class WindowsBackend(PlatformBackend):
    """Windows backend scaffold."""

    def _unsupported(self, operation: str) -> NoReturn:
        raise UnsupportedOperationError(operation, "windows")

    def supports(self, capability: str) -> bool:
        if capability == "powershell":
            return self._powershell_executable() is not None
        return capability in {
            "system_info",
            "file_operations",
            "gui_editors",
            "process_execution",
        }

    @staticmethod
    def _powershell_executable() -> Optional[str]:
        return shutil.which("powershell.exe") or shutil.which("pwsh.exe")

    def _run_powershell(
        self, script: str, timeout: int = RUN_TIMEOUT_SECONDS
    ) -> Optional[subprocess.CompletedProcess]:
        executable = self._powershell_executable()
        if executable is None:
            return None
        try:
            return subprocess.run(
                [
                    executable,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    def _powershell_output(self, script: str) -> Optional[str]:
        result = self._run_powershell(script)
        if result is None or result.returncode != 0:
            return None
        output = result.stdout.strip()
        return output or None

    def _compile_then_run(self, compile_args: List[str], run_args: List[str]) -> None:
        compile_result = self.run_and_capture(compile_args, timeout=RUN_TIMEOUT_SECONDS)
        if compile_result is None:
            return
        if compile_result.returncode != 0:
            print("Compiler errors are shown above.")
            return
        self.run_and_capture(run_args, timeout=RUN_TIMEOUT_SECONDS)

    # --- System Information ---

    def get_gpu_info(self) -> str:
        output = self._powershell_output(
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name, DriverVersion, AdapterRAM | "
            "Format-Table -AutoSize | Out-String -Width 200"
        )
        return output or "GPU information is unavailable."

    def get_battery_info(self) -> str:
        output = self._powershell_output(
            "Get-CimInstance Win32_Battery | "
            "Select-Object Name, EstimatedChargeRemaining, BatteryStatus | "
            "Format-Table -AutoSize | Out-String -Width 200"
        )
        return output or "No battery information found."

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
        output = self._powershell_output(
            "Get-CimInstance Win32_ComputerSystem | "
            "Select-Object -ExpandProperty UserName"
        )
        return output or "Logged-in user information is unavailable."

    def get_running_processes(self) -> str:
        output = self._powershell_output(
            "Get-Process | Sort-Object WorkingSet64 -Descending | "
            "Select-Object -First 10 Id, ProcessName, "
            "@{Name='MemoryMB';Expression={[math]::Round($_.WorkingSet64 / 1MB, 1)}} | "
            "Format-Table -AutoSize | Out-String -Width 200"
        )
        return output or "Running process information is unavailable."

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
        executable = shutil.which("fastfetch.exe") or shutil.which("fastfetch")
        if executable:
            try:
                result = subprocess.run(
                    [executable],
                    capture_output=True,
                    text=True,
                    timeout=RUN_TIMEOUT_SECONDS,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                result = None
            if result is not None and result.returncode == 0:
                return result.stdout.rstrip()

        return "\n\n".join(
            (
                "fastfetch is not installed. Showing fallback system information instead.",
                self.get_os_info(),
                self.get_cpu_info(),
                self.get_memory_usage(),
                self.get_disk_usage(),
            )
        )

    # --- File Operations ---

    def create_file(self, path: Path) -> bool:
        path.touch(exist_ok=True)
        return True

    def create_directory(self, path: Path) -> bool:
        path.mkdir(exist_ok=False)
        return True

    def copy_file(self, source: Path, destination: Path) -> bool:
        shutil.copy2(source, destination)
        return True

    def make_executable(self, path: Path) -> bool:
        return self._unsupported("make_executable")

    def edit_file(self, path: Path, editor: str) -> bool:
        editor_config = EDITORS.get(editor)
        if editor_config is None:
            return False

        executable = editor_config["command"][0]
        resolved_executable = self.which(executable)
        if not resolved_executable:
            print(f"Editor not available: {editor}")
            return False

        args = [resolved_executable, *editor_config["command"][1:], str(path)]
        if Path(resolved_executable).suffix.lower() in {".bat", ".cmd"}:
            args = [
                os.environ.get("COMSPEC", "cmd.exe"),
                "/d",
                "/c",
                "call",
                *args,
            ]
        try:
            if editor_config["gui"]:
                subprocess.Popen(
                    args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                )
            else:
                subprocess.run(args, check=False)
        except OSError as error:
            print(f"Could not open {editor}: {error}")
            return False
        return True

    def run_file(self, path: Path) -> bool:
        output_path = path.with_suffix(".exe")
        runners = {
            ".py": lambda: self.run_and_capture([sys.executable, str(path)], timeout=RUN_TIMEOUT_SECONDS),
            ".c": lambda: self._compile_then_run(
                ["gcc", str(path), "-o", str(output_path)], [str(output_path)]
            ),
            ".cpp": lambda: self._compile_then_run(
                ["g++", str(path), "-o", str(output_path)], [str(output_path)]
            ),
            ".java": lambda: self._compile_then_run(
                ["javac", str(path)], ["java", "-cp", str(path.parent), path.stem]
            ),
            ".js": lambda: self.run_and_capture(["node", str(path)], timeout=RUN_TIMEOUT_SECONDS),
            ".go": lambda: self.run_and_capture(["go", "run", str(path)], timeout=RUN_TIMEOUT_SECONDS),
            ".rs": lambda: self._compile_then_run(
                ["rustc", str(path), "-o", str(output_path)], [str(output_path)]
            ),
        }
        runner = runners.get(path.suffix.lower())
        if runner is None:
            return False
        runner()
        return True

    def extract_zip(self, archive_path: Path, extract_to: Path) -> int:
        return self._unsupported("extract_zip")

    # --- Process Execution ---

    def run_command(
        self, args: List[str], cwd: Optional[Path] = None
    ) -> Optional[subprocess.CompletedProcess]:
        powershell_commands = {
            ("ls",): "Get-ChildItem | Select-Object Mode, LastWriteTime, Length, Name | Format-Table -AutoSize",
            ("pwd",): "Get-Location | Select-Object -ExpandProperty Path",
        }
        script = powershell_commands.get(tuple(args))
        if script is not None:
            result = self._run_powershell(script)
            if result is None:
                print("PowerShell is unavailable.")
                return None
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print("Errors:")
                print(result.stderr, end="")
            return result

        try:
            return subprocess.run(args, cwd=cwd, check=False)
        except FileNotFoundError:
            print(f"Command not available: {args[0]}")
            return None

    def launch_background(self, args: List[str]) -> bool:
        if not args:
            return False
        executable = "calc.exe" if args[0] == "gnome-calculator" else args[0]
        resolved_executable = shutil.which(executable)
        if resolved_executable is None:
            print(f"Command not available: {executable}")
            return False
        try:
            subprocess.Popen([resolved_executable, *args[1:]])
        except OSError as error:
            print(f"Could not launch {executable}: {error}")
            return False
        return True

    def run_and_capture(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        timeout: int = 10,
    ) -> Optional[subprocess.CompletedProcess]:
        try:
            result = subprocess.run(
                args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            print(f"Command not available: {args[0]}")
            return None
        except subprocess.TimeoutExpired:
            print(f"Stopped after {timeout} seconds because the program took too long.")
            return None

        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print("Errors:")
            print(result.stderr, end="")
        return result

    # --- Platform Capabilities ---

    def has_display(self) -> bool:
        return True

    def which(self, command: str) -> Optional[str]:
        return shutil.which(command)

    def get_shell(self) -> str:
        return self._powershell_executable() or os.environ.get("COMSPEC", "Unknown shell")

    def get_editor_command(self, editor_name: str) -> Optional[List[str]]:
        editor = EDITORS.get(editor_name)
        return editor["command"] if editor else None

    def is_editor_gui(self, editor_name: str) -> bool:
        editor = EDITORS.get(editor_name)
        return bool(editor and editor["gui"])

    def get_supported_editors(self) -> Dict[str, Dict[str, Any]]:
        return EDITORS.copy()

    # --- Utility ---

    def get_workspace_dir(self) -> Path:
        return self.get_project_dir() / "workspace"

    def get_project_dir(self) -> Path:
        return Path.cwd().resolve()

    def validate_filename(self, name: str) -> bool:
        return bool(name) and not any(part in name for part in BLOCKED_NAME_PARTS)

    def get_safe_path(self, filename: str) -> Optional[Path]:
        if not self.validate_filename(filename):
            return None
        workspace = self.get_workspace_dir()
        workspace.mkdir(exist_ok=True)
        path = (workspace / filename).resolve()
        return path if path.parent == workspace.resolve() else None

    def safe_name(self, name: str, label: str) -> Optional[Path]:
        if not self.validate_filename(name):
            return None
        project = self.get_project_dir()
        candidate = (project / name).resolve()
        return candidate if candidate.parent == project else None
