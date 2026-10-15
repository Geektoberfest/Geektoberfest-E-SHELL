import io
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import commands
from model import predict_intent


class IntentRoutingBaseTestCase(unittest.TestCase):
    """Base setup for intent routing tests providing an isolated sandbox directory and stdout capture."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="eshell_intent_test_")
        self.project_dir = Path(self.test_dir) / "project"
        self.project_dir.mkdir()
        self.workspace_dir = self.project_dir / "workspace"
        self.workspace_dir.mkdir()

        self.orig_project_dir = commands.PROJECT_DIR
        self.orig_workspace_dir = commands.WORKSPACE_DIR
        commands.PROJECT_DIR = self.project_dir
        commands.WORKSPACE_DIR = self.workspace_dir

    def tearDown(self):
        commands.PROJECT_DIR = self.orig_project_dir
        commands.WORKSPACE_DIR = self.orig_workspace_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def capture_command(self, text):
        buf = io.StringIO()
        with redirect_stdout(buf):
            commands.handle_command(text)
        return buf.getvalue()


class StructuredIntentRoutingTests(IntentRoutingBaseTestCase):
    """Structured, parameterized tests verifying natural language phrases reach their exact handlers."""

    ALL_NAMED_HANDLERS = [
        "show_disk_usage",
        "show_memory_usage",
        "show_system_uptime",
        "show_kernel_info",
        "show_cpu_info",
        "show_current_user",
        "show_hostname",
        "show_os_info",
        "show_gpu_info",
        "show_battery_info",
        "show_network_info",
        "show_logged_in_users",
        "show_running_processes",
        "show_environment_info",
        "show_python_version",
        "show_package_manager_info",
        "show_fastfetch_info",
        "handle_version",
    ]

    # 1. Parameterized tests for representative system information intents
    def test_system_info_intent_routing_table(self):
        """Verify that representative natural-language phrases route to their specific handlers."""
        # Table of: (phrase, expected_intent, expected_handler_name)
        routing_table = [
            # Disk usage
            ("disk usage", "disk_usage", "show_disk_usage"),
            ("storage info", "disk_usage", "show_disk_usage"),
            ("disk space", "disk_usage", "show_disk_usage"),
            # CPU info
            ("cpu info", "cpu_info", "show_cpu_info"),
            ("processor details", "cpu_info", "show_cpu_info"),
            ("show cpu", "cpu_info", "show_cpu_info"),
            # Memory usage
            ("memory usage", "memory_usage", "show_memory_usage"),
            ("ram usage", "memory_usage", "show_memory_usage"),
            ("free memory", "memory_usage", "show_memory_usage"),
            # System uptime
            ("system uptime", "system_uptime", "show_system_uptime"),
            ("uptime", "system_uptime", "show_system_uptime"),
            ("how long has the system been running", "system_uptime", "show_system_uptime"),
            # Kernel info
            ("kernel info", "kernel_info", "show_kernel_info"),
            ("system kernel", "kernel_info", "show_kernel_info"),
            ("kernel details", "kernel_info", "show_kernel_info"),
            # Current user
            ("current user", "current_user", "show_current_user"),
            ("logged in user", "current_user", "show_current_user"),
            ("show current user", "current_user", "show_current_user"),
            # Hostname
            ("hostname", "hostname", "show_hostname"),
            ("computer name", "hostname", "show_hostname"),
            ("machine name", "hostname", "show_hostname"),
            # OS info
            ("os info", "os_info", "show_os_info"),
            ("operating system info", "os_info", "show_os_info"),
            ("show os information", "os_info", "show_os_info"),
            # GPU info
            ("gpu info", "gpu_info", "show_gpu_info"),
            ("graphics card info", "gpu_info", "show_gpu_info"),
            ("show gpu", "gpu_info", "show_gpu_info"),
            # Battery info
            ("battery info", "battery_info", "show_battery_info"),
            ("battery status", "battery_info", "show_battery_info"),
            ("show battery", "battery_info", "show_battery_info"),
            # Network info
            ("network info", "network_info", "show_network_info"),
            ("show network", "network_info", "show_network_info"),
            ("network interfaces", "network_info", "show_network_info"),
            # IP address (routes to show_network_info)
            ("ip address", "ip_address", "show_network_info"),
            ("show ip address", "ip_address", "show_network_info"),
            ("what is my ip", "ip_address", "show_network_info"),
            # Logged in users
            ("logged in users", "logged_in_users", "show_logged_in_users"),
            ("who is logged in", "logged_in_users", "show_logged_in_users"),
            ("show logged in users", "logged_in_users", "show_logged_in_users"),
            # Running processes
            ("running processes", "running_processes", "show_running_processes"),
            ("show processes", "running_processes", "show_running_processes"),
            ("top memory processes", "running_processes", "show_running_processes"),
            # Environment info
            ("environment info", "environment_info", "show_environment_info"),
            ("environment variables", "environment_info", "show_environment_info"),
            ("show environment", "environment_info", "show_environment_info"),
            # Python version
            ("python version", "python_version", "show_python_version"),
            ("show python version", "python_version", "show_python_version"),
            ("which python version", "python_version", "show_python_version"),
            # Package manager info
            ("package manager info", "package_manager_info", "show_package_manager_info"),
            ("package manager", "package_manager_info", "show_package_manager_info"),
            ("which package manager", "package_manager_info", "show_package_manager_info"),
            # Fastfetch info
            ("fastfetch info", "fastfetch_info", "show_fastfetch_info"),
            ("system summary", "fastfetch_info", "show_fastfetch_info"),
            ("show fastfetch", "fastfetch_info", "show_fastfetch_info"),
            # Version
            ("version", "version", "handle_version"),
            ("VERSION", "version", "handle_version"),
        ]

        # Patch all handlers simultaneously to ensure no unrelated handler is called
        handler_patches = {
            name: patch.object(commands, name) for name in self.ALL_NAMED_HANDLERS
        }
        mocked_handlers = {name: p.start() for name, p in handler_patches.items()}

        try:
            for phrase, expected_intent, expected_handler in routing_table:
                with self.subTest(phrase=phrase, expected_intent=expected_intent):
                    # Reset all mocks before each phrase
                    for mock in mocked_handlers.values():
                        mock.reset_mock()

                    # 1. Verify model predicts the expected intent
                    predicted = predict_intent(phrase)
                    self.assertEqual(
                        predicted,
                        expected_intent,
                        f"Phrase '{phrase}' predicted intent '{predicted}', expected '{expected_intent}'",
                    )

                    # 2. Execute command and verify target handler is invoked
                    self.capture_command(phrase)
                    mocked_handlers[expected_handler].assert_called_once()

                    # 3. Verify NO other handler was invoked
                    for handler_name, mock in mocked_handlers.items():
                        if handler_name != expected_handler:
                            mock.assert_not_called()
        finally:
            for p in handler_patches.values():
                p.stop()

    # 2. Command execution intents (run_command)
    @patch("commands.run_command")
    def test_run_command_intents_routing(self, mock_run_command):
        """Verify list_files and current_dir invoke run_command with exact argument lists."""
        table = [
            ("list files", "list_files", ["ls"]),
            ("show files", "list_files", ["ls"]),
            ("display files", "list_files", ["ls"]),
            ("current directory", "current_dir", ["pwd"]),
            ("where am i", "current_dir", ["pwd"]),
            ("present directory", "current_dir", ["pwd"]),
        ]

        for phrase, expected_intent, expected_args in table:
            with self.subTest(phrase=phrase):
                mock_run_command.reset_mock()
                self.assertEqual(predict_intent(phrase), expected_intent)
                self.capture_command(phrase)
                mock_run_command.assert_called_once_with(expected_args)

    # 3. GUI launcher intents (launch_background)
    @patch("commands.launch_background")
    @patch("commands.predict_intent")
    def test_gui_launcher_intents_routing(self, mock_predict, mock_launch):
        """Verify open_firefox and calculator intents invoke launch_background with exact argument lists."""
        table = [
            ("open_firefox", ["firefox"]),
            ("calculator", ["gnome-calculator"]),
        ]

        for intent, expected_args in table:
            with self.subTest(intent=intent):
                mock_launch.reset_mock()
                mock_predict.return_value = intent
                self.capture_command("dummy launcher request")
                mock_launch.assert_called_once_with(expected_args)

    # 4. Built-in output intents (shell_info, date_time)
    def test_shell_info_intent_routing(self):
        """Verify shell info intent reads from SHELL environment variable."""
        with patch.dict("os.environ", {"SHELL": "/bin/custom_zsh"}):
            output = self.capture_command("shell info")
            self.assertIn("/bin/custom_zsh", output)

    def test_date_time_intent_routing(self):
        """Verify date_time intent prints formatted timestamp."""
        for phrase in ("date", "time", "current time"):
            with self.subTest(phrase=phrase):
                output = self.capture_command(phrase)
                self.assertRegex(output, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")

    # 5. File action routing (keyword-based operations)
    def test_file_action_routing_table(self):
        """Verify direct file operations and friendly aliases route to correct handlers with arguments."""
        file_actions = [
            ("touch notes.txt", "handle_touch", ["touch", "notes.txt"]),
            ("create file report.txt", "handle_touch", ["touch", "report.txt"]),
            ("mkdir project_dir", "handle_mkdir", ["mkdir", "project_dir"]),
            ("create folder my_folder", "handle_mkdir", ["mkdir", "my_folder"]),
            ("cp src.txt dst.txt", "handle_copy", ["cp", "src.txt", "dst.txt"]),
            ("copy src.txt to dst.txt", "handle_copy", ["cp", "src.txt", "dst.txt"]),
            ("edit script.py", "handle_edit", ["edit", "script.py"]),
            ("open main.py in nano", "handle_edit", ["open", "main.py", "in", "nano"]),
            ("make script.sh executable", "handle_make_executable", ["make", "script.sh", "executable"]),
            ("run code.py", "handle_run_file", ["run", "code.py"]),
            ("unzip archive.zip", "handle_unzip", ["unzip", "archive.zip"]),
            ("extract package.zip", "handle_unzip", ["extract", "package.zip"]),
        ]

        action_names = [
            "handle_touch",
            "handle_mkdir",
            "handle_copy",
            "handle_edit",
            "handle_make_executable",
            "handle_run_file",
            "handle_unzip",
        ]
        action_patches = {name: patch.object(commands, name) for name in action_names}
        mocked_actions = {name: p.start() for name, p in action_patches.items()}

        try:
            for cmd_text, expected_handler, expected_args in file_actions:
                with self.subTest(command=cmd_text):
                    for mock in mocked_actions.values():
                        mock.reset_mock()

                    self.capture_command(cmd_text)
                    mocked_actions[expected_handler].assert_called_once_with(expected_args)

                    for handler_name, mock in mocked_actions.items():
                        if handler_name != expected_handler:
                            mock.assert_not_called()
        finally:
            for p in action_patches.values():
                p.stop()

    # 6. Exhaustive intent dispatcher verification
    @patch("commands.predict_intent")
    @patch("commands.run_command")
    @patch("commands.launch_background")
    def test_exhaustive_dispatcher_routes_all_supported_intents(
        self, mock_launch, mock_run_cmd, mock_predict
    ):
        """Verify all 25 intents registered in handle_command route to their dedicated handler."""
        handler_patches = {
            name: patch.object(commands, name) for name in self.ALL_NAMED_HANDLERS
        }
        mocked_handlers = {name: p.start() for name, p in handler_patches.items()}

        try:
            intent_to_target = {
                "list_files": ("run_command", ["ls"]),
                "current_dir": ("run_command", ["pwd"]),
                "disk_usage": ("handler", "show_disk_usage"),
                "memory_usage": ("handler", "show_memory_usage"),
                "date_time": ("stdout", None),
                "system_uptime": ("handler", "show_system_uptime"),
                "kernel_info": ("handler", "show_kernel_info"),
                "cpu_info": ("handler", "show_cpu_info"),
                "current_user": ("handler", "show_current_user"),
                "hostname": ("handler", "show_hostname"),
                "open_firefox": ("launch_background", ["firefox"]),
                "calculator": ("launch_background", ["gnome-calculator"]),
                "os_info": ("handler", "show_os_info"),
                "gpu_info": ("handler", "show_gpu_info"),
                "battery_info": ("handler", "show_battery_info"),
                "network_info": ("handler", "show_network_info"),
                "ip_address": ("handler", "show_network_info"),
                "logged_in_users": ("handler", "show_logged_in_users"),
                "running_processes": ("handler", "show_running_processes"),
                "environment_info": ("handler", "show_environment_info"),
                "shell_info": ("stdout", None),
                "python_version": ("handler", "show_python_version"),
                "package_manager_info": ("handler", "show_package_manager_info"),
                "fastfetch_info": ("handler", "show_fastfetch_info"),
                "version": ("handler", "handle_version"),
            }

            for intent, (target_type, target_val) in intent_to_target.items():
                with self.subTest(intent=intent):
                    mock_predict.return_value = intent
                    mock_run_cmd.reset_mock()
                    mock_launch.reset_mock()
                    for mock in mocked_handlers.values():
                        mock.reset_mock()

                    output = self.capture_command("trigger phrase")

                    if target_type == "handler":
                        mocked_handlers[target_val].assert_called_once()
                    elif target_type == "run_command":
                        mock_run_cmd.assert_called_once_with(target_val)
                    elif target_type == "launch_background":
                        mock_launch.assert_called_once_with(target_val)
                    elif target_type == "stdout":
                        self.assertTrue(len(output) > 0)

                    # Ensure no unintended named handler was invoked
                    for h_name, mock in mocked_handlers.items():
                        if target_type == "handler" and h_name == target_val:
                            continue
                        mock.assert_not_called()
        finally:
            for p in handler_patches.values():
                p.stop()


class UnknownAndUnsupportedInputRoutingTests(IntentRoutingBaseTestCase):
    """Verify that unknown, out-of-scope, empty, or malformed input never executes accidental commands."""

    @patch("commands.subprocess.run")
    @patch("commands.subprocess.Popen")
    @patch("commands.run_command")
    @patch("commands.launch_background")
    def test_random_text_and_out_of_scope_phrases_run_nothing(
        self, mock_launch, mock_run_cmd, mock_popen, mock_run
    ):
        """Random text and out-of-scope requests must display unknown guidance and execute nothing."""
        unsupported_inputs = [
            "blorp_xyz_unknown_command",
            "asdfghjkl zxcvbnm",
            "play some jazz music",
            "send an email to my manager",
            "buy groceries online",
            "what is the stock price of Apple",
            "restart apache server",
        ]

        for text in unsupported_inputs:
            with self.subTest(input=text):
                output = self.capture_command(text)
                self.assertIn("did not run anything", output)
                self.assertIn("Type 'help' to see example commands", output)
                mock_run.assert_not_called()
                mock_popen.assert_not_called()
                mock_run_cmd.assert_not_called()
                mock_launch.assert_not_called()

    @patch("commands.subprocess.run")
    @patch("commands.subprocess.Popen")
    @patch("commands.predict_intent")
    def test_empty_and_whitespace_inputs_trigger_nothing(self, mock_predict, mock_popen, mock_run):
        """Empty or whitespace-only inputs must exit cleanly without routing."""
        for text in ("", "   ", "\t", "\n", " \t \n "):
            with self.subTest(input=repr(text)):
                output = self.capture_command(text)
                self.assertEqual(output, "")
                mock_predict.assert_not_called()
                mock_run.assert_not_called()
                mock_popen.assert_not_called()

    @patch("commands.subprocess.run")
    @patch("commands.subprocess.Popen")
    @patch("commands.predict_intent")
    def test_malformed_quoted_inputs_report_error_and_run_nothing(
        self, mock_predict, mock_popen, mock_run
    ):
        """Unclosed quotes must report a parse error and execute nothing."""
        malformed_inputs = [
            'touch "unclosed_filename.txt',
            "mkdir 'missing_end_quote",
            'cp "source.txt destination.txt',
        ]

        for text in malformed_inputs:
            with self.subTest(input=text):
                output = self.capture_command(text)
                self.assertIn("could not read that input", output)
                mock_predict.assert_not_called()
                mock_run.assert_not_called()
                mock_popen.assert_not_called()

    @patch("commands.subprocess.run")
    @patch("commands.subprocess.Popen")
    @patch("commands.predict_intent")
    def test_blocked_dangerous_commands_are_prevented(
        self, mock_predict, mock_popen, mock_run
    ):
        """Dangerous commands must be blocked immediately before any routing or execution."""
        dangerous_commands = [
            "rm -rf /",
            "rmdir /var",
            "mv important.txt deleted.txt",
            "sudo apt update",
            "kill -9 1234",
            "shutdown -h now",
            "reboot",
            "chmod 777 script.sh",
            "chown root file.txt",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs /dev/sda1",
        ]

        for cmd in dangerous_commands:
            with self.subTest(command=cmd):
                output = self.capture_command(cmd)
                self.assertIn("Blocked dangerous command.", output)
                mock_predict.assert_not_called()
                mock_run.assert_not_called()
                mock_popen.assert_not_called()


class ExternalSideEffectMockingTests(IntentRoutingBaseTestCase):
    """Verify that external side effects (subprocess, GUI, file modifications) are completely stubbed."""

    @patch("commands.subprocess.run")
    def test_system_commands_never_invoke_host_binaries(self, mock_run):
        """Invoking system info commands executes through mocked subprocess.run without host impact."""
        mock_run.return_value = MagicMock(returncode=0, stdout="mocked output", stderr="")
        commands.run_command(["ls"])
        mock_run.assert_called_once_with(["ls"], check=False)

    @patch("commands.subprocess.Popen")
    def test_gui_launchers_never_spawn_host_processes(self, mock_popen):
        """Launching GUI programs executes through mocked subprocess.Popen without opening windows."""
        commands.launch_background(["firefox"])
        mock_popen.assert_called_once_with(["firefox"])

    def test_file_operations_confined_to_test_sandbox(self):
        """File operations never escape or modify paths outside the temporary project directory."""
        self.capture_command("touch sandboxed_file.txt")
        created = self.project_dir / "sandboxed_file.txt"
        self.assertTrue(created.is_file())
        self.assertTrue(created.is_relative_to(self.project_dir))


class IntentRouterIntegrityAndRegressionTests(IntentRoutingBaseTestCase):
    """Verify router integrity, fallback safety, and regression protection."""

    @patch("commands.run_command")
    @patch("commands.launch_background")
    @patch("commands.predict_intent")
    def test_classifier_hallucinated_file_actions_are_safely_ignored(
        self, mock_predict, mock_launch, mock_run_command
    ):
        """If the ML classifier hallucinates a file action intent, E-SHELL must refuse to execute it."""
        unroutable_intents = [
            "edit_file",
            "make_executable",
            "run_file",
            "unzip_file",
            "fake_admin_intent",
            "arbitrary_execution",
        ]

        for intent in unroutable_intents:
            with self.subTest(intent=intent):
                mock_predict.return_value = intent
                output = self.capture_command("natural language phrase")
                self.assertIn("did not run anything", output)
                mock_run_command.assert_not_called()
                mock_launch.assert_not_called()

    def test_help_command_always_available(self):
        """Help command is always recognized and displays usage guidance."""
        output = self.capture_command("help")
        self.assertIn("Available examples:", output)
        self.assertIn("disk usage", output)
        self.assertIn("File safety rules:", output)


if __name__ == "__main__":
    unittest.main()
