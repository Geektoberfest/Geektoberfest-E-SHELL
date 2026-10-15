import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

import commands


class SystemToolsTests(unittest.TestCase):
    """Unit and regression tests for system tools integration (Issue #16)."""

    def capture_output(self, command_text):
        buf = io.StringIO()
        with redirect_stdout(buf):
            commands.handle_command(command_text)
        return buf.getvalue()

    # Scenario 1: Supported utility is installed and launches successfully
    @patch("commands.find_tool_executable", return_value="/usr/bin/htop")
    @patch("commands.subprocess.run")
    def test_supported_tool_installed_launches_successfully(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(returncode=0)
        output = self.capture_output("htop")
        mock_find.assert_called_with("htop")
        mock_run.assert_called_once_with(["/usr/bin/htop"], check=False)
        self.assertEqual(output, "")

    # Scenario 2: Supported utility is missing
    @patch("commands.find_tool_executable", return_value=None)
    def test_supported_tool_missing_shows_actionable_error(self, mock_find):
        output = self.capture_output("btop")
        self.assertIn("'btop' is not installed or is not on PATH", output)
        self.assertIn("Visual resource monitor", output)
        self.assertIn("To install it:", output)
        self.assertIn("sudo apt install btop", output)

    # Scenario 3: Unsupported or invalid tool name is supplied
    @patch("commands.predict_intent", return_value="unknown")
    def test_unsupported_or_invalid_tool_name_falls_through_to_unknown(self, _mock_predict):
        output = self.capture_output("nonexistent_tool_xyz")
        self.assertIn("I didn't understand \"nonexistent_tool_xyz\"", output)

    # Scenario 4: Arguments and flags are forwarded correctly
    @patch("commands.find_tool_executable", return_value="/usr/bin/htop")
    @patch("commands.subprocess.run")
    def test_arguments_and_flags_forwarded_correctly(self, mock_run, _mock_find):
        mock_run.return_value = MagicMock(returncode=0)
        self.capture_output("htop -d 15 -u testuser")
        mock_run.assert_called_once_with(
            ["/usr/bin/htop", "-d", "15", "-u", "testuser"], check=False
        )

    # Scenario 5: Paths and arguments containing spaces are handled correctly
    @patch("commands.find_tool_executable", return_value="/usr/bin/locate")
    @patch("commands.subprocess.run")
    def test_paths_and_arguments_with_spaces_preserved(self, mock_run, _mock_find):
        mock_run.return_value = MagicMock(returncode=0)
        self.capture_output('locate "project report 2026.pdf"')
        mock_run.assert_called_once_with(
            ["/usr/bin/locate", "project report 2026.pdf"], check=False
        )

    # Scenario 6: Executable detection behaves correctly on supported operating systems
    @patch("commands.shutil.which")
    def test_executable_detection_primary_and_fallback(self, mock_which):
        def which_side_effect(cmd):
            if cmd == "locate":
                return None
            if cmd == "plocate":
                return "/usr/bin/plocate"
            return None

        mock_which.side_effect = which_side_effect
        # locate should fall back to plocate if locate binary is missing
        resolved = commands.find_tool_executable("locate")
        self.assertEqual(resolved, "/usr/bin/plocate")

    @patch("commands.shutil.which")
    def test_executable_detection_when_all_missing(self, mock_which):
        mock_which.return_value = None
        self.assertIsNone(commands.find_tool_executable("btop"))
        self.assertIsNone(commands.find_tool_executable("ncdu"))

    # Scenario 7: Interactive applications receive appropriate terminal handling
    @patch("commands.find_tool_executable", return_value="/usr/bin/ncdu")
    @patch("commands.subprocess.run")
    def test_interactive_tool_terminal_execution(self, mock_run, _mock_find):
        mock_run.return_value = MagicMock(returncode=0)
        self.capture_output("ncdu /home/user")
        # Subprocess must run with direct stdio inheritance (no capture_output)
        mock_run.assert_called_once_with(["/usr/bin/ncdu", "/home/user"], check=False)

    # Scenario 8: Launch failures and non-zero exit codes are handled correctly
    @patch("commands.find_tool_executable", return_value="/usr/bin/htop")
    @patch("commands.subprocess.run")
    def test_launch_failure_permission_error(self, mock_run, _mock_find):
        mock_run.side_effect = PermissionError("Permission denied")
        output = self.capture_output("htop")
        self.assertIn("Permission denied when attempting to run 'htop'", output)

    @patch("commands.find_tool_executable", return_value="/usr/bin/htop")
    @patch("commands.subprocess.run")
    def test_launch_failure_os_error(self, mock_run, _mock_find):
        mock_run.side_effect = OSError("Exec format error")
        output = self.capture_output("htop")
        self.assertIn("Could not run 'htop': Exec format error", output)

    @patch("commands.find_tool_executable", return_value="/usr/bin/htop")
    @patch("commands.subprocess.run")
    def test_launch_keyboard_interrupt_handled_cleanly(self, mock_run, _mock_find):
        mock_run.side_effect = KeyboardInterrupt()
        output = self.capture_output("htop")
        # Should not raise exception or crash
        self.assertEqual(output.strip(), "")

    @patch("commands.find_tool_executable", return_value="/usr/bin/locate")
    @patch("commands.subprocess.run")
    def test_non_zero_exit_code_handled_without_crash(self, mock_run, _mock_find):
        mock_run.return_value = MagicMock(returncode=1)
        # locate exiting 1 on no results should return cleanly
        output = self.capture_output("locate missing_pattern")
        self.assertEqual(output, "")

    # Scenario 9: Existing built-in commands and arbitrary command execution remain unaffected
    @patch("commands.show_disk_usage")
    @patch("commands.predict_intent", return_value="disk_usage")
    def test_existing_builtins_unaffected(self, _mock_predict, mock_disk):
        self.capture_output("disk usage")
        mock_disk.assert_called_once()

    def test_blocked_commands_remain_blocked(self):
        output = self.capture_output("rm -rf /")
        self.assertIn("Blocked dangerous command", output)

    # Scenario 10: Empty input and malformed tool configuration are handled appropriately
    def test_empty_input_handled_cleanly(self):
        output = self.capture_output("")
        self.assertEqual(output, "")

    def test_locate_without_pattern_gives_friendly_guidance(self):
        output = self.capture_output("locate")
        self.assertIn("Please provide a search pattern, for example: locate filename", output)

    def test_unknown_system_tool_resolution_returns_none(self):
        self.assertIsNone(commands.resolve_system_tool("not_a_tool"))
        self.assertIsNone(commands.resolve_system_tool(""))

    # Scenario 11: Duplicate tool definitions or aliases do not cause conflicts
    def test_aliases_resolve_correctly(self):
        self.assertEqual(commands.resolve_system_tool("lazyfit"), "lazygit")
        self.assertEqual(commands.resolve_system_tool("plocate"), "locate")
        self.assertEqual(commands.resolve_system_tool("mlocate"), "locate")

    @patch("commands.find_tool_executable", return_value="/usr/bin/lazygit")
    @patch("commands.subprocess.run")
    def test_alias_lazyfit_executes_lazygit(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(returncode=0)
        self.capture_output("lazyfit")
        mock_find.assert_called_with("lazygit")
        mock_run.assert_called_once_with(["/usr/bin/lazygit"], check=False)

    # Scenario 12: Documentation examples match the actual implementation
    def test_all_documented_candidate_tools_exist_in_registry(self):
        expected_tools = {"htop", "btop", "ncdu", "locate", "tig", "lazygit", "tree", "fzf"}
        for tool in expected_tools:
            with self.subTest(tool=tool):
                self.assertIn(tool, commands.SYSTEM_TOOLS)
                config = commands.SYSTEM_TOOLS[tool]
                self.assertIn("description", config)
                self.assertIn("commands", config)
                self.assertIn("package", config)
                self.assertIn("packages", config)

    # System tools status command tests
    def test_tools_status_command_displays_all_tools(self):
        output = self.capture_output("tools")
        self.assertIn("Available System Tools:", output)
        for tool in ("htop", "btop", "ncdu", "locate", "tig", "lazygit", "tree", "fzf"):
            self.assertIn(tool, output)

    def test_system_tools_alias_displays_all_tools(self):
        output = self.capture_output("system tools")
        self.assertIn("Available System Tools:", output)


if __name__ == "__main__":
    unittest.main()
