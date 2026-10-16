import pytest

import platforms
from platforms.linux import LinuxBackend


@pytest.fixture(autouse=True)
def default_legacy_tests_to_linux(monkeypatch):
    """Keep existing Linux regression tests independent of the host OS."""
    monkeypatch.setattr(platforms.platform, "system", lambda: "Linux")
    monkeypatch.setattr(LinuxBackend, "which", lambda _self, command: command)
