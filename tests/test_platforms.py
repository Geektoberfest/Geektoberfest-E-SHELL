import inspect
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

import platforms.linux as linux_module
import platforms.windows as windows_module
from platforms import get_backend
from platforms.base import PlatformBackend
from platforms.errors import BackendNotImplementedError, UnsupportedOperationError
from platforms.linux import LinuxBackend
from platforms.windows import WindowsBackend


@pytest.mark.parametrize(
    ("os_name", "backend_type"),
    (("Linux", LinuxBackend), ("Windows", WindowsBackend)),
)
def test_selects_backend_for_runtime_os(monkeypatch, os_name, backend_type):
    monkeypatch.setattr("platforms.platform.system", lambda: os_name)

    assert isinstance(get_backend(), backend_type)


def test_rejects_unsupported_platform(monkeypatch):
    monkeypatch.setattr("platforms.platform.system", lambda: "FreeBSD")

    with pytest.raises(BackendNotImplementedError) as error:
        get_backend()

    assert error.value.platform == "FreeBSD"


@pytest.mark.parametrize("backend_type", (LinuxBackend, WindowsBackend))
def test_backends_fulfill_the_abstract_contract(backend_type):
    assert not inspect.isabstract(backend_type)

    backend = backend_type()
    for method_name in PlatformBackend.__abstractmethods__:
        assert callable(getattr(backend, method_name))


@pytest.mark.parametrize("backend_type", (LinuxBackend, WindowsBackend))
def test_backends_share_core_capabilities(backend_type):
    backend = backend_type()

    assert backend.supports("system_info")
    assert backend.supports("process_execution")
    assert backend.supports("file_operations")
    assert backend.supports("gui_editors")
    assert not backend.supports("unknown_capability")


@pytest.mark.parametrize("backend_type", (LinuxBackend, WindowsBackend))
def test_backends_share_safe_file_operations(backend_type, tmp_path):
    backend = backend_type()
    source = tmp_path / "source.txt"
    destination = tmp_path / "destination.txt"
    directory = tmp_path / "folder"

    assert backend.create_file(source)
    source.write_text("content")
    assert backend.copy_file(source, destination)
    assert backend.create_directory(directory)

    assert destination.read_text() == "content"
    assert directory.is_dir()
    assert backend.validate_filename("notes.txt")
    assert not backend.validate_filename("../outside.txt")
    assert backend.run_file(Path("notes.txt")) is False


@pytest.mark.parametrize("backend_type", (LinuxBackend, WindowsBackend))
def test_zip_extraction_is_explicitly_unsupported(backend_type, tmp_path):
    backend = backend_type()

    with pytest.raises(UnsupportedOperationError) as error:
        backend.extract_zip(tmp_path / "archive.zip", tmp_path)

    assert error.value.operation == "extract_zip"


def test_windows_executable_permission_is_unsupported(tmp_path):
    backend = WindowsBackend()

    with pytest.raises(UnsupportedOperationError) as error:
        backend.make_executable(tmp_path / "script.py")

    assert error.value.operation == "make_executable"
    assert error.value.platform == "windows"


def test_windows_powershell_uses_fixed_argument_list(monkeypatch):
    backend = WindowsBackend()
    result = subprocess.CompletedProcess([], 0, stdout="GPU output\n", stderr="")
    run = Mock(return_value=result)
    monkeypatch.setattr(backend, "_powershell_executable", lambda: "powershell.exe")
    monkeypatch.setattr(windows_module.subprocess, "run", run)

    assert backend.get_gpu_info() == "GPU output"

    args = run.call_args.args[0]
    assert args[:5] == [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
    ]
    assert len(args) == 6
    assert "Win32_VideoController" in args[5]
    assert "shell" not in run.call_args.kwargs
    assert run.call_args.kwargs["timeout"] == 10


def test_windows_powershell_absence_fails_safely(monkeypatch):
    backend = WindowsBackend()
    run = Mock()
    monkeypatch.setattr(backend, "_powershell_executable", lambda: None)
    monkeypatch.setattr(windows_module.subprocess, "run", run)

    assert backend.get_gpu_info() == "GPU information is unavailable."
    assert backend.get_battery_info() == "No battery information found."
    assert backend.get_logged_in_users() == "Logged-in user information is unavailable."
    assert backend.get_running_processes() == "Running process information is unavailable."
    run.assert_not_called()


def test_windows_powershell_timeout_fails_safely(monkeypatch):
    backend = WindowsBackend()
    monkeypatch.setattr(backend, "_powershell_executable", lambda: "powershell.exe")
    monkeypatch.setattr(
        windows_module.subprocess,
        "run",
        Mock(side_effect=subprocess.TimeoutExpired("powershell.exe", 10)),
    )

    assert backend._run_powershell("Get-Process") is None


def test_windows_pwd_routes_through_powershell(monkeypatch, capsys):
    backend = WindowsBackend()
    result = subprocess.CompletedProcess([], 0, stdout="C:\\project\n", stderr="")
    run_powershell = Mock(return_value=result)
    monkeypatch.setattr(backend, "_run_powershell", run_powershell)

    returned = backend.run_command(["pwd"])

    assert returned is result
    assert capsys.readouterr().out == "C:\\project\n"
    assert "Get-Location" in run_powershell.call_args.args[0]


def test_windows_missing_background_program_fails_safely(monkeypatch, capsys):
    backend = WindowsBackend()
    popen = Mock()
    monkeypatch.setattr(windows_module.shutil, "which", lambda _command: None)
    monkeypatch.setattr(windows_module.subprocess, "Popen", popen)

    assert backend.launch_background(["missing-program"]) is False
    assert "Command not available" in capsys.readouterr().out
    popen.assert_not_called()


def test_windows_cmd_editor_uses_command_interpreter(monkeypatch, tmp_path):
    backend = WindowsBackend()
    popen = Mock()
    launcher = "C:\\Tools\\code.cmd"
    monkeypatch.setattr(backend, "which", lambda _command: launcher)
    monkeypatch.setattr(windows_module.subprocess, "Popen", popen)

    assert backend.edit_file(tmp_path / "notes.txt", "code")

    args = popen.call_args.args[0]
    assert args[1:4] == ["/d", "/c", "call"]
    assert args[4] == launcher
    assert args[-1] == str(tmp_path / "notes.txt")


def test_linux_command_execution_uses_argument_list(monkeypatch):
    backend = LinuxBackend()
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(linux_module.subprocess, "run", run)

    backend.run_command(["ls", "-la"])

    run.assert_called_once_with(["ls", "-la"], cwd=None, check=False)


def test_linux_missing_tool_does_not_start_process(monkeypatch):
    backend = LinuxBackend()
    run = Mock()
    monkeypatch.setattr(linux_module.shutil, "which", lambda _command: None)
    monkeypatch.setattr(linux_module.subprocess, "run", run)

    assert "lspci is not installed" in backend.get_gpu_info()
    run.assert_not_called()


def test_linux_display_detection_uses_environment(monkeypatch):
    backend = LinuxBackend()
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert not backend.has_display()

    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    assert backend.has_display()
