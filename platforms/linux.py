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


"""
EDITORS now consist all the editors that can be used from REPL.
"EDITOR" : { "EditorName": ["cmd"], "type", ""}
"""
EDITORS = {
    "nano": {"command": ["nano"], "gui": False},
    "vim": {"command": ["vim"], "gui": False},
    "micro": {"command": ["micro"], "gui": False},
    "helix": {"command": ["hx"], "gui": False},
    "emacs": {"command": ["emacs", "-nw"], "gui": False},
    "gedit": {"command": ["gedit"], "gui": True},
}
RUN_TIMEOUT_SECONDS = 10
BLOCKED_NAME_PARTS = ("/", "..", "~", "*", "?", "&", "|", ";", "$", "`", ">", "<")


class LinuxBackend(PlatformBackend):

    def supports(self, capability: str) -> bool:
        """Return capabilities implemented by this backend."""
        return capability in {"system_info", "process_execution", "file_operations", "gui_editors"}

    @staticmethod
    def _capture(args: List[str], check_available: bool = True) -> Optional[str]:
        """Run a known-safe command and return its standard output."""
        if check_available and not shutil.which(args[0]):
            return None
        try:
            result = subprocess.run(args, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return None
        return result.stdout.rstrip()

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
        if not uptime_file.is_file():
            return "System uptime is unavailable (uptime not installed)."
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
            sections.append(self._capture(command, check_available=False) or f" Command not available: {command[0]}")
        return "\n\n".join(sections)

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
        try:
            subprocess.run(["chmod", "+x", str(path)], check=False)
        except FileNotFoundError:
            print("Command not available: chmod")
            return False
        return True

    def edit_file(self, path: Path, editor: str) -> bool:
        editor_config = EDITORS.get(editor)
        if editor_config is None:
            return False

        executable = editor_config["command"][0]
        if not self.which(executable):
            print(f"Editor not available: {editor}")
            return False
        if editor_config["gui"] and not self.has_display():
            print(f"'{editor}' needs a graphical display and none was found. Try nano, vim, or micro.")
            return False

        args = [*editor_config["command"], str(path)]
        try:
            if editor_config["gui"]:
                subprocess.Popen(
                    args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            else:
                subprocess.run(args, check=False)
        except FileNotFoundError:
            print(f"Editor not available: {editor}")
            return False
        except OSError as error:
            print(f"Could not open {editor}: {error}")
            return False
        return True

    def run_file(self, path: Path) -> bool:
        runners = {
            ".py": lambda: self.run_and_capture(["python3", str(path)], timeout=RUN_TIMEOUT_SECONDS),
            ".c": lambda: self._compile_then_run(["gcc", str(path), "-o", str(path.with_suffix(""))], [str(path.with_suffix(""))]),
            ".cpp": lambda: self._compile_then_run(["g++", str(path), "-o", str(path.with_suffix(""))], [str(path.with_suffix(""))]),
            ".java": lambda: self._compile_then_run(["javac", str(path)], ["java", "-cp", str(path.parent), path.stem]),
            ".js": lambda: self.run_and_capture(["node", str(path)], timeout=RUN_TIMEOUT_SECONDS),
            ".sh": lambda: self.run_and_capture(["bash", str(path)], timeout=RUN_TIMEOUT_SECONDS),
            ".go": lambda: self.run_and_capture(["go", "run", str(path)], timeout=RUN_TIMEOUT_SECONDS),
            ".rs": lambda: self._compile_then_run(["rustc", str(path), "-o", str(path.with_suffix(""))], [str(path.with_suffix(""))]),
        }
        runner = runners.get(path.suffix)
        if runner is None:
            return False
        runner()
        return True

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
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def which(self, command: str) -> Optional[str]:
        return shutil.which(command)

    def get_shell(self) -> str:
        return os.environ.get("SHELL", "Unknown shell")

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
