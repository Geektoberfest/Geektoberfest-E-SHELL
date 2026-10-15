# e-shell semantic versioning
"""
e-shell version

classfication of versioning
SemVer	             Bump it when
MAJOR (1.0.0)	     breaking changes, or the first stable release
MINOR (0.2.0)	     new features that don’t break anything
PATCH (0.1.1)	     bug fixes only


also prints bunch of other useful information like dependencies and other system runtime info

"""
import os
import platform
import time
START = time.monotonic() # instant internal time clock measured
import re
from importlib.metadata import PackageNotFoundError, requires, version
from pathlib import Path

__version__ = "1.0.0"

# It will be the second the program is launched ( yk __ __ thingy in python )
REQUIREMENTS = Path(__file__).resolve().parent / "requirements.txt"
LOGO = Path(__file__).resolve().parent / "logo.txt"

# Matches the bare distribution name and stops before ==, >=, [extras] or ;markers.
# the REGEX :D
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

try:
    import resource      # Unix only, (premature)
except ImportError:
    resource = None



def tracked_packages():
    """Read the direct dependency names out of requirements.txt.
    """
    names = []
    try:
        text = REQUIREMENTS.read_text(encoding="utf-8")
    except OSError:
        return names

    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()  # drop comments
        if not line or line.startswith("-"):  # skip blanks and -r / -e / --flags
            continue

        match = NAME_PATTERN.match(line)
        if match:
            names.append(match.group(0))

    return names



def with_transitive(names): 
    """ with_transitive
    Expand the direct dependencies one level deep, so the output stays short.

    requirements.txt lists direct dependencies only, which hides the packages that
    actually break the .pkl files (numpy, scipy, joblib behind scikit-learn).

    The function which might blow the Information lists.
    """

    # seen because we don't have more than 2 libraries to print their own NUMPY and JSON dependencies to print again
    seen = list(names)
    for name in names:
        try:
            required = requires(name) or []
        except PackageNotFoundError:
            continue

        for req in required:
            if "extra ==" in req:  # skip optional extras
                continue

            match = NAME_PATTERN.match(req)
            if not match:
                continue

            dep = match.group(0)
            if dep not in seen:
                seen.append(dep)

    return seen



def dependency_lines():
    """ dependency_lines()
    One ``name version`` line per tracked package, for the version output.
    Well, it prints the data in a formatted way that's all :D
    """

    names = tracked_packages()
    if not names:
        return ["requirements.txt not found or empty"]

    lines = []
    for name in with_transitive(names):
        try:
            lines.append(f"{name} {version(name)}")
        except PackageNotFoundError:
            lines.append(f"{name}: not installed")

    return lines

def usage_line():
    """PID, session uptime and peak memory of the running shell.
    simple line to show PID, UPTIME(runtime of program), peak memory"""

    line = f"PID {os.getpid()} | uptime {time.monotonic() - START:.0f}s"
    if resource:
        peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        line += f" | peak memory {peak_mb:.1f} MB"
    return line


# Fallback banner used when logo.txt cannot be read, so startup never crashes.
_FALLBACK_LOGO = r"""
  ______      _____ _          _ _
 |  ____|    / ____| |        | | |
 | |__ _____| (___ | |__   ___| | |
 |  __|______\___ \| '_ \ / _ \ | |
 | |____     ____) | | | |  __/ | |
 |______|   |_____/|_| |_|\___|_|_|
"""


def load_logo() -> str:
    """Read the ASCII logo from ``logo.txt`` next to this module.

    Returns the logo as a string with trailing blank lines removed. If the
    file is missing or unreadable, a small built-in fallback is returned so
    that the banner still prints.
    """
    try:
        return LOGO.read_text(encoding="utf-8").rstrip()
    except OSError:
        return _FALLBACK_LOGO.strip("\n")


def show_intro() -> None:
    """Print the startup banner: the E-SHELL logo, version and runtime info.

    Everything below the logo is cosmetic, so failures are swallowed rather
    than aborting the shell before the user can type a command.
    """
    print(load_logo())
    print(f"  E-SHELL v{__version__}")

    try:
        print(f"  Python {platform.python_version()} on {platform.system()}")
    except Exception:  # pragma: no cover - platform info is best effort
        pass

    print()
    print("  Type 'help' to see available commands")
    print("  Type 'exit' to quit")
    print()
