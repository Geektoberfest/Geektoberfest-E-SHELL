import datetime
import os
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

from model import predict_intent
from platforms import get_backend
from version import __version__, dependency_lines, usage_line
from platforms.errors import UnsupportedOperationError
import settings

# These commands are intentionally read-only or very limited.  Dangerous actions
# such as rm, mv, chmod, chown, sudo, shutdown, reboot, kill, mkfs, and dd are
# blocked by design because a beginner-friendly assistant should not be able to
# delete data, change permissions, or damage the system by accident.
BLOCKED_NAME_PARTS = ("/", "..", "~", "*", "?", "&", "|", ";", "$", "`", ">", "<")
BLOCKED_COMMANDS = {
    "rm",
    "rmdir",
    "mv",
    "sudo",
    "kill",
    "shutdown",
    "reboot",
    "chmod",
    "chown",
    "dd",
    "mkfs",
}
PROJECT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_DIR / "workspace"
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
SYSTEM_TOOLS = {
    "htop": {
        "description": "Interactive process and system monitor",
        "commands": ["htop"],
        "package": "htop",
        "interactive": True,
        "packages": {
            "apt": "sudo apt install htop",
            "dnf": "sudo dnf install htop",
            "pacman": "sudo pacman -S htop",
            "zypper": "sudo zypper install htop",
            "apk": "apk add htop",
            "brew": "brew install htop",
        },
    },
    "btop": {
        "description": "Visual resource monitor showing CPU, memory, disks, network, and processes",
        "commands": ["btop"],
        "package": "btop",
        "interactive": True,
        "packages": {
            "apt": "sudo apt install btop",
            "dnf": "sudo dnf install btop",
            "pacman": "sudo pacman -S btop",
            "zypper": "sudo zypper install btop",
            "apk": "apk add btop",
            "brew": "brew install btop",
        },
    },
    "ncdu": {
        "description": "Interactive NCurses disk usage analyzer",
        "commands": ["ncdu"],
        "package": "ncdu",
        "interactive": True,
        "packages": {
            "apt": "sudo apt install ncdu",
            "dnf": "sudo dnf install ncdu",
            "pacman": "sudo pacman -S ncdu",
            "zypper": "sudo zypper install ncdu",
            "apk": "apk add ncdu",
            "brew": "brew install ncdu",
        },
    },
    "locate": {
        "description": "Fast file searching using an indexed database",
        "commands": ["locate", "plocate", "mlocate"],
        "package": "plocate",
        "interactive": False,
        "packages": {
            "apt": "sudo apt install plocate",
            "dnf": "sudo dnf install plocate",
            "pacman": "sudo pacman -S plocate",
            "zypper": "sudo zypper install mlocate",
            "apk": "apk add mlocate",
            "brew": "brew install findutils",
        },
    },
    "tig": {
        "description": "Text-mode interface for Git repository history and diff browsing",
        "commands": ["tig"],
        "package": "tig",
        "interactive": True,
        "packages": {
            "apt": "sudo apt install tig",
            "dnf": "sudo dnf install tig",
            "pacman": "sudo pacman -S tig",
            "zypper": "sudo zypper install tig",
            "apk": "apk add tig",
            "brew": "brew install tig",
        },
    },
    "lazygit": {
        "description": "Terminal-based user interface for Git operations",
        "commands": ["lazygit"],
        "package": "lazygit",
        "interactive": True,
        "packages": {
            "apt": "sudo apt install lazygit",
            "dnf": "sudo dnf install lazygit",
            "pacman": "sudo pacman -S lazygit",
            "zypper": "sudo zypper install lazygit",
            "apk": "apk add lazygit",
            "brew": "brew install lazygit",
        },
    },
    "tree": {
        "description": "Recursive directory listing displayed as a depth-indented tree",
        "commands": ["tree"],
        "package": "tree",
        "interactive": False,
        "packages": {
            "apt": "sudo apt install tree",
            "dnf": "sudo dnf install tree",
            "pacman": "sudo pacman -S tree",
            "zypper": "sudo zypper install tree",
            "apk": "apk add tree",
            "brew": "brew install tree",
        },
    },
    "fzf": {
        "description": "Command-line interactive fuzzy finder",
        "commands": ["fzf"],
        "package": "fzf",
        "interactive": True,
        "packages": {
            "apt": "sudo apt install fzf",
            "dnf": "sudo dnf install fzf",
            "pacman": "sudo pacman -S fzf",
            "zypper": "sudo zypper install fzf",
            "apk": "apk add fzf",
            "brew": "brew install fzf",
        },
    },
}
TOOL_ALIASES = {
    "lazyfit": "lazygit",
    "plocate": "locate",
    "mlocate": "locate",
}
RUN_TIMEOUT_SECONDS = 10
# ZIP extraction limits keep a single archive from filling the disk.
MAX_ZIP_ENTRIES = 200
MAX_ZIP_UNPACKED_BYTES = 20 * 1024 * 1024
APPROVED_RUN_FILES = set()


def resolve_system_tool(name):
    """Return the canonical tool name if recognized, or None."""
    if not name:
        return None
    lowered = name.lower()
    canonical = TOOL_ALIASES.get(lowered, lowered)
    if canonical in SYSTEM_TOOLS:
        return canonical
    return None


def find_tool_executable(canonical):
    """Find and return the executable path for a supported system tool, or None."""
    config = SYSTEM_TOOLS.get(canonical)
    if not config:
        return None
    for cmd in config.get("commands", []):
        found = shutil.which(cmd)
        if found:
            return found
    return None


def get_warn_prefix():
    """Return a warning symbol that can safely be encoded by the active stdout stream."""
    encoding = getattr(sys.stdout, "encoding", None)
    if encoding:
        try:
            "⚠️".encode(encoding)
            return "⚠️"
        except UnicodeEncodeError:
            return "[!]"
    return "⚠️"


def get_tool_install_instructions(canonical):
    """Format clear, actionable installation instructions for a missing tool."""
    config = SYSTEM_TOOLS.get(canonical)
    if not config:
        return f"Tool '{canonical}' is not recognized."

    warn = get_warn_prefix()
    pkg_name = config.get("package", canonical)
    lines = [
        f"{warn} '{canonical}' is not installed or is not on PATH.",
        f"   Description: {config['description']}",
        "   To install it:",
    ]

    detected_managers = [
        m for m in ("apt", "dnf", "pacman", "zypper", "apk", "brew") if shutil.which(m)
    ]
    packages = config.get("packages", {})

    if detected_managers:
        for pm in detected_managers:
            if pm in packages:
                lines.append(f"     {packages[pm]}")
    else:
        for pm, install_cmd in packages.items():
            lines.append(f"     {install_cmd}")

    if platform.system() == "Windows":
        lines.append(f"     winget install {pkg_name}  (or via scoop/choco)")

    return "\n".join(lines)


def handle_system_tool(tool_name, user_args=None):
    """Execute a supported system tool with user arguments, or show installation instructions."""
    if user_args is None:
        user_args = []

    canonical = resolve_system_tool(tool_name)
    if not canonical:
        print(f"Unknown system tool: {tool_name}")
        return False

    if canonical == "locate" and not user_args:
        print("Please provide a search pattern, for example: locate filename")
        return False

    executable = find_tool_executable(canonical)
    if not executable:
        print(get_tool_install_instructions(canonical))
        return False

    full_args = [executable, *user_args]
    warn = get_warn_prefix()
    try:
        result = subprocess.run(full_args, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        print(f"{warn} Command not available: {executable}")
        return False
    except PermissionError:
        print(f"{warn} Permission denied when attempting to run '{canonical}'.")
        return False
    except OSError as error:
        print(f"{warn} Could not run '{canonical}': {error}")
        return False
    except KeyboardInterrupt:
        print()
        return False


def show_system_tools_status():
    """Display all supported system tools, descriptions, and installation statuses."""
    print("Available System Tools:")
    print("-" * 65)
    for name, config in SYSTEM_TOOLS.items():
        installed = find_tool_executable(name) is not None
        status = "[installed]" if installed else "[not installed]"
        print(f"  {name:<10} - {config['description']}")
        print(f"               Status: {status} (package: {config['package']})")
    print("-" * 65)
    print("Run any tool directly by name, e.g. 'htop', 'ncdu', 'tree', or 'locate <pattern>'.")


def run_command(args):
    return get_backend().run_command(args)


def launch_background(args):
    return get_backend().launch_background(args)


def validate_filename(name):
    """Return True only for simple filenames allowed in the workspace."""
    if not name:
        print("Please provide a file name.")
        return False

    if any(part in name for part in BLOCKED_NAME_PARTS):
        print(
            "Blocked unsafe filename. Use a simple name without /, .., ~, *, ?, &, |, ;, $, `, >, or <."
        )
        return False

    return True


def get_safe_path(filename):
    """Build a safe path inside workspace/ after validating the filename."""
    if not validate_filename(filename):
        return None

    WORKSPACE_DIR.mkdir(exist_ok=True)
    path = (WORKSPACE_DIR / filename).resolve()
    if path.parent != WORKSPACE_DIR.resolve():
        print("Blocked path outside the workspace folder.")
        return None

    return path


def print_help():
    print(
        """
Available examples:
  disk usage              cpu info                os info
  gpu info                battery info            network info
  ip address              logged in users         running processes
  environment info        shell info              python version
  package manager info    fastfetch info          
  touch notes.txt         mkdir examples          cp notes.txt backup.txt
  create file notes.txt   create folder examples  copy notes.txt to backup.txt
  edit hello.py           open hello.py in nano   open hello.py in vim
  make hello.py executable
  run hello.py            unzip project.zip       version

System tools:
  htop                    btop                    ncdu
  locate <pattern>        tig                     lazygit
  tree                    fzf                     tools

File safety rules:
  - Only simple names in the current project directory are allowed.
  - Paths and shell symbols such as /, .., ~, *, ?, &, |, ;, $, `, >, < are blocked.
  - Editing, chmod +x, and running are limited to files inside workspace/.
  - unzip only extracts a .zip from workspace/ into workspace/ and refuses unsafe archives.
  - Destructive commands are intentionally not supported.
""".strip()
    )


def safe_name(name, label):
    """Accept only one simple filename/folder name inside this project folder."""
    if not name:
        print(f"Please provide a {label} name.")
        return None

    if any(part in name for part in BLOCKED_NAME_PARTS):
        print(
            "Blocked unsafe name. Use a simple name without /, .., ~, *, ?, &, |, ;, $, `, >, or <."
        )
        return None

    candidate = (PROJECT_DIR / name).resolve()
    if candidate.parent != PROJECT_DIR:
        print("Blocked path outside the current project directory.")
        return None

    return candidate


def parse_words(text):
    try:
        return shlex.split(text)
    except ValueError:
        print("I could not read that input. Please check the quotes and try again.")
        return []


def handle_edit(words):
    command = words[0].lower()
    backend = get_backend()

    if len(words) == 2 and command in {"edit", "open"}: # two values to value through
        filename = words[1]
        editor = choose_default_editor()
    elif len(words) == 4 and command == "open" and words[2].lower() == "in":
        filename = words[1]
        editor = words[3].lower()
    else:   # last fallback for Warning & early return
        print("Please use: edit filename, open filename, or open filename in <editor>")
        return
        
    # sanity check for available Editors in EDITORS~
    if editor not in backend.get_supported_editors():
        supported = ", ".join(backend.get_supported_editors())
        print(f"Unsupported editor. Supported editors: {supported}.")
        return

    path = get_safe_path(filename)
    if not path:
        return

    if backend.edit_file(path, editor):
        record_editor_use(editor)


# the best sanity check
# helpful if somebody is SSH into Linux based machine or using WSLg (wsl2 might give windowsub-pop)
def choose_default_editor():
    # if user has set a global default with envVAR
    override = os.environ.get("E_SHELL_DEFAULT_EDITOR", "").strip().lower()
    backend = get_backend()
    editors = backend.get_supported_editors()
    if override in editors and backend.which(editors[override]["command"][0]):
        return override
    
    # called from settings
    usage = settings.get("editor_usage")
    if not isinstance(usage, dict):
        usage = {}
    
    # a Checklist of rules to let editors be actually usa-blegive 
    usable = {
        name: count
        for name, count in usage.items()
        if name in editors
        and isinstance(count, int)
        and count > 0
        and backend.which(editors[name]["command"][0])
        and (not editors[name]["gui"] or backend.has_display())
    }

    if usable:
        return max(usable, key=usable.get)

    for name, config in editors.items():
        if backend.which(config["command"][0]) and (
            not config["gui"] or backend.has_display()
        ):
            return name

    return next(iter(editors), "nano")


def record_editor_use(name):
    usage = settings.get("editor_usage")
    if not isinstance(usage, dict):
        usage = {}

    count = usage.get(name, 0)
    if not isinstance(count, int):           
        count = 0

    usage[name] = usage.get(name, 0) + 1
    settings.set("editor_usage", usage)


def handle_make_executable(words):
    if len(words) != 3 or words[0].lower() != "make" or words[2].lower() != "executable":
        print("Please use: make filename executable")
        return

    path = get_safe_path(words[1])
    if not path:
        return
    if not path.is_file():
        print(f"File does not exist in workspace: {path.name}")
        return
      
    try:
        if get_backend().make_executable(path):
            print(f"Made executable: {path.name}")
    except UnsupportedOperationError:
        print("Making files executable is not supported on this platform.")

    



def ask_before_first_run(path):
    if path in APPROVED_RUN_FILES:
        return True

    answer = input(
        f"Running code can be unsafe. Run workspace/{path.name}? Type yes to continue: "
    )
    if answer.strip().lower() != "yes":
        print("Run cancelled.")
        return False

    APPROVED_RUN_FILES.add(path)
    return True


def handle_run_file(words):
    if len(words) != 2:
        print("Please provide one file name, for example: run hello.py")
        return

    path = get_safe_path(words[1])
    if not path:
        return
    if not path.is_file():
        print(f"File does not exist in workspace: {path.name}")
        return
    if not ask_before_first_run(path):
        return

    if not get_backend().run_file(path):
        print("Unsupported file type. Supported: .py, .c, .cpp, .java, .js, .sh, .go, .rs")


class ZipExtractionError(Exception):
    """Raised when writing archive entries fails; anything written is undone first."""


def check_zip_member(info):
    """Return (relative parts, None) for a safe archive entry, or (None, reason)."""
    name = info.filename
    if "\0" in name:
        return None, "the name contains a null character"
    if "\\" in name:
        return None, "the name contains a backslash"
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return None, "the path is absolute"

    parts = [part for part in name.split("/") if part not in ("", ".")]
    if not parts:
        return None, "the name is empty"
    if ".." in parts:
        return None, "the path uses .. to leave the folder"
    for part in parts:
        if any(blocked in part for blocked in BLOCKED_NAME_PARTS if blocked != "/"):
            return None, "the name contains a blocked character"

    if info.flag_bits & 0x1:
        return None, "the entry is encrypted"

    file_type = stat.S_IFMT(info.external_attr >> 16)
    if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
        return None, "links and special files are not allowed"

    return parts, None


def plan_zip_extraction(archive):
    """Check every entry first. Returns (entries, None) or (None, message)."""
    infos = archive.infolist()
    if not infos:
        return None, "the archive is empty"
    if len(infos) > MAX_ZIP_ENTRIES:
        return None, f"it has {len(infos)} entries (limit {MAX_ZIP_ENTRIES})"

    total_bytes = sum(info.file_size for info in infos)
    if total_bytes > MAX_ZIP_UNPACKED_BYTES:
        return None, (
            f"it would unpack to {total_bytes // (1024 * 1024)} MB "
            f"(limit {MAX_ZIP_UNPACKED_BYTES // (1024 * 1024)} MB)"
        )

    workspace = WORKSPACE_DIR.resolve()
    entries = []
    seen = set()
    for info in infos:
        parts, reason = check_zip_member(info)
        if reason:
            return None, f"unsafe entry '{info.filename}': {reason}"

        target = (workspace.joinpath(*parts)).resolve()
        if not target.is_relative_to(workspace) or target == workspace:
            return None, f"unsafe entry '{info.filename}': it resolves outside workspace/"
        if target in seen:
            return None, f"entry '{info.filename}' appears more than once"
        seen.add(target)

        is_dir = info.is_dir()
        if target.exists() and not (is_dir and target.is_dir()):
            return None, f"'{info.filename}' already exists in workspace/ and would be overwritten"
        entries.append((info, target, is_dir))

    return entries, None


def write_zip_entries(archive, entries):
    """Extract planned entries. Undo everything if any entry fails. Returns file count."""
    created = []
    written = 0
    try:
        for info, target, is_dir in entries:
            if is_dir:
                if not target.exists():
                    target.mkdir(parents=True)
                    created.append(target)
                continue

            for parent in reversed(target.parents):
                if parent == WORKSPACE_DIR.resolve() or parent.exists():
                    continue
                parent.mkdir()
                created.append(parent)

            # "xb" refuses to overwrite and never follows an existing link.
            with archive.open(info) as source, open(target, "xb") as destination:
                created.append(target)
                remaining = MAX_ZIP_UNPACKED_BYTES - written
                data = source.read(remaining + 1)
                if len(data) > remaining:
                    raise ValueError("the archive unpacks to more data than it declared")
                destination.write(data)
                written += len(data)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        for path in reversed(created):
            try:
                path.rmdir() if path.is_dir() else path.unlink()
            except OSError:
                pass
        raise ZipExtractionError(str(error)) from error

    return sum(1 for _, _, is_dir in entries if not is_dir)


def handle_unzip(words):
    if len(words) != 2:
        print("Please provide one archive name, for example: unzip project.zip")
        return

    path = get_safe_path(words[1])
    if not path:
        return
    if path.suffix.lower() != ".zip":
        print("Only .zip archives are supported.")
        return
    if not path.is_file():
        print(f"File does not exist in workspace: {path.name}")
        return

    try:
        with zipfile.ZipFile(path) as archive:
            entries, problem = plan_zip_extraction(archive)
            if problem:
                print(f"Blocked unsafe archive {path.name}: {problem}. Nothing was extracted.")
                return
            count = write_zip_entries(archive, entries)
    except ZipExtractionError as error:
        print(f"Could not extract {path.name}: {error}. Nothing was extracted.")
        return
    except zipfile.BadZipFile:
        print(f"Could not extract {path.name}: it is not a valid zip file. Nothing was extracted.")
        return
    except OSError as error:
        print(f"Could not read {path.name}: {error.strerror or error}.")
        return

    print(f"Extracted {count} file(s) from {path.name} into workspace/")


def handle_touch(words):
    if len(words) < 2:
        print("Please provide a file name, for example: touch notes.txt")
        return
    if len(words) > 2:
        print("Please provide only one file name, for example: touch notes.txt")
        return

    path = safe_name(words[1], "file")
    if path:
        if get_backend().create_file(path):
            print(f"Created file: {path.name}")


def handle_mkdir(words):
    if len(words) < 2:
        print("Please provide a folder name, for example: mkdir examples")
        return
    if len(words) > 2:
        print("Please provide only one folder name, for example: mkdir examples")
        return

    path = safe_name(words[1], "folder")
    if not path:
        return

    try:
        if get_backend().create_directory(path):
            print(f"Created folder: {path.name}")
    except FileExistsError:
        print(f"Folder already exists: {path.name}")


def handle_copy(words):
    if len(words) < 3:
        print("Please provide a source and destination, for example: cp notes.txt backup.txt")
        return
    if len(words) > 3:
        print("Please provide only a source and destination, for example: cp notes.txt backup.txt")
        return

    source = safe_name(words[1], "source file")
    destination = safe_name(words[2], "destination file")
    if not source or not destination:
        return
    if not source.is_file():
        print(f"Source file does not exist: {source.name}")
        return

    if get_backend().copy_file(source, destination):
        print(f"Copied {source.name} to {destination.name}")


def show_gpu_info():
    print(get_backend().get_gpu_info())


def show_battery_info():
    print(get_backend().get_battery_info())


def show_environment_info():
    for key, value in get_backend().get_environment_info().items():
        print(f"{key}={value}")


def show_running_processes():
    print(get_backend().get_running_processes())


def show_disk_usage():
    print(get_backend().get_disk_usage())


def show_memory_usage():
    print(get_backend().get_memory_usage())


def show_system_uptime():
    print(get_backend().get_system_uptime())


def show_kernel_info():
    print(get_backend().get_kernel_info())


def show_cpu_info():
    print(get_backend().get_cpu_info())


def show_current_user():
    print(get_backend().get_current_user())


def show_hostname():
    print(get_backend().get_hostname())


def show_os_info():
    print(get_backend().get_os_info())


def show_network_info():
    print(get_backend().get_network_info())


def show_logged_in_users():
    print(get_backend().get_logged_in_users())


def show_python_version():
    print(get_backend().get_python_version())


def show_package_manager_info():
    print(get_backend().get_package_manager_info())


def handle_version():
    model_files = ["intent_model.pkl", "vectorizer.pkl"]
    found = all((Path(PROJECT_DIR) / f).exists() for f in model_files)

    # whole custom printing stash
    lines = [
        f"E-SHELL v{__version__}",
        f"Python {platform.python_version()} ({sys.executable})",
        f"OS: {platform.platform()}",
        "",
        "Dependencies:",
        *[f"  {line}" for line in dependency_lines()],
        "",
        f"Model files: {'found' if found else 'MISSING'}",
        f"Project dir: {PROJECT_DIR}",
        usage_line(),
    ]
    print("\n".join(lines))

def show_fastfetch_info():
    print(get_backend().get_fastfetch_info())


def print_unknown_feedback(text):
    """Explain that nothing was run and point the user to help or a rephrase."""
    print(f"❓ I didn't understand \"{text}\", so I did not run anything.")
    print("   - Type 'help' to see example commands.")
    print("   - Or try rephrasing, for example: 'disk usage', 'cpu info', or 'who am i'.")


def handle_command(text):
    words = parse_words(text)
    if not words:
        return

    first_word = words[0].lower()
    lowered_words = [word.lower() for word in words]
    if first_word in BLOCKED_COMMANDS or lowered_words[:2] == ["chmod", "777"]:
        print("Blocked dangerous command.")
        return
    if first_word == "help":
        print_help()
        return
    if first_word == "touch":
        handle_touch(words)
        return
    if first_word == "mkdir":
        handle_mkdir(words)
        return
    if first_word == "cp":
        handle_copy(words)
        return
    if first_word == "edit" or (
        first_word == "open"
        and (
            (len(words) == 2 and words[1].lower() not in {"firefox", "calculator"})
            or (len(words) == 4 and words[2].lower() == "in")
        )
    ):
        handle_edit(words)
        return
    if first_word == "make" and lowered_words[-1] == "executable":
        handle_make_executable(words)
        return
    if first_word == "run":
        handle_run_file(words)
        return
    if first_word in ("unzip", "extract"):
        handle_unzip(words)
        return

    # Friendly aliases keep file operations easier to discover while still
    # reusing the same strict validation as the terminal-style forms above.
    if words[:2] == ["create", "file"]:
        handle_touch(["touch", *words[2:]])
        return
    if words[:2] == ["create", "folder"]:
        handle_mkdir(["mkdir", *words[2:]])
        return
    if len(words) >= 1 and words[0] == "copy":
        if len(words) == 4 and words[2] == "to":
            handle_copy(["cp", words[1], words[3]])
        else:
            print("Please use: copy source to destination")
        return

    if (
        first_word in ("tools", "system_tools")
        or lowered_words[:2] in (["system", "tools"], ["show", "tools"], ["list", "tools"])
    ):
        show_system_tools_status()
        return

    if resolve_system_tool(first_word):
        handle_system_tool(first_word, words[1:])
        return

    intent = predict_intent(text)
    DEBUG = os.environ.get("ESHELL_DEBUG", "").lower() in {"1", "true", "yes", "on"}

    if DEBUG:
        print(f"[DEBUG] Predicted intent: {intent}")

    backend = get_backend()
    handlers = {
        "list_files": lambda: run_command(["ls"]),
        "current_dir": lambda: run_command(["pwd"]),
        "disk_usage": show_disk_usage,
        "memory_usage": show_memory_usage,
        "date_time": lambda: print(datetime.datetime.now()),
        "system_uptime": show_system_uptime,
        "kernel_info": show_kernel_info,
        "cpu_info": show_cpu_info,
        "current_user": show_current_user,
        "hostname": show_hostname,
        "open_firefox": lambda: launch_background(["firefox"]),
        "calculator": lambda: launch_background(["gnome-calculator"]),
        "os_info": show_os_info,
        "gpu_info": show_gpu_info,
        "battery_info": show_battery_info,
        "network_info": show_network_info,
        "ip_address": show_network_info,
        "logged_in_users": show_logged_in_users,
        "running_processes": show_running_processes,
        "environment_info": show_environment_info,
        "shell_info": lambda: print(backend.get_shell()),
        "python_version": show_python_version,
        "package_manager_info": show_package_manager_info,
        "fastfetch_info": show_fastfetch_info,
        "version": handle_version,
    }

    handler = handlers.get(intent)
    if handler:
        handler()
    else:
        print_unknown_feedback(text)
