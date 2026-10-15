import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from platforms import get_backend
from platforms.errors import BackendNotImplementedError
from platforms.linux import LinuxBackend


class PlatformSelectionTests(unittest.TestCase):
    @patch("platforms.platform.system", return_value="Linux")
    def test_selects_linux_backend(self, _system):
        self.assertIsInstance(get_backend(), LinuxBackend)

    @patch("platforms.platform.system", return_value="FreeBSD")
    def test_rejects_unsupported_platform(self, _system):
        with self.assertRaises(BackendNotImplementedError) as context:
            get_backend()

        self.assertEqual(context.exception.platform, "FreeBSD")


class LinuxBackendTests(unittest.TestCase):
    def setUp(self):
        self.backend = LinuxBackend()

    def test_reports_implemented_capabilities(self):
        self.assertTrue(self.backend.supports("system_info"))
        self.assertTrue(self.backend.supports("process_execution"))
        self.assertTrue(self.backend.supports("file_operations"))
        self.assertTrue(self.backend.supports("gui_editors"))
        self.assertFalse(self.backend.supports("powershell"))

    @patch("platforms.linux.subprocess.run")
    def test_run_command_uses_safe_argument_list(self, run):
        self.backend.run_command(["ls", "-la"])

        run.assert_called_once_with(["ls", "-la"], cwd=None, check=False)

    def test_file_operations_create_and_copy_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            destination = Path(directory) / "destination.txt"

            self.assertTrue(self.backend.create_file(source))
            source.write_text("content")
            self.assertTrue(self.backend.copy_file(source, destination))

            self.assertEqual(destination.read_text(), "content")

    def test_unsupported_file_type_is_not_run(self):
        self.assertFalse(self.backend.run_file(Path("notes.txt")))

    def test_environment_info_has_expected_keys(self):
        environment = self.backend.get_environment_info()

        self.assertEqual(set(environment), {"USER", "HOME", "SHELL", "LANG", "TERM", "PATH"})

    def test_display_detection_uses_linux_display_variables(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(self.backend.has_display())
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=True):
            self.assertTrue(self.backend.has_display())

    def test_safe_name_rejects_paths_outside_the_project(self):
        self.assertIsNone(self.backend.safe_name("../outside.txt", "file"))


if __name__ == "__main__":
    unittest.main()
