# Platform Compatibility & Command Fallbacks Guide

E-SHELL is designed to operate seamlessly across both **Linux** and **Windows** environments through its modular `PlatformBackend` architecture (`platforms/base.py`). This guide details external command dependencies, built-in graceful fallbacks when system binaries are missing, distro package manager commands, and the Windows compatibility layer.

---

## 1. Architecture Overview

E-SHELL decouples intent classification and command parsing from operating system specifics:

```
User Input ───► Intent Classifier / REPL
                     │
                     ▼
          commands.py (Handlers)
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   LinuxBackend          WindowsBackend
(platforms/linux.py)  (platforms/windows.py)
```

- **`LinuxBackend`**: Implements POSIX-compliant system inspection, shell utilities, coreutils wrappers, and fallbacks to `/proc`, `/sys`, and the Python standard library.
- **`WindowsBackend`**: Implements native Windows command translations via PowerShell, WMI/CIM cmdlets (`Get-CimInstance`), Windows command-line tools (`ipconfig`, `tasklist`, `whoami`), and Windows-native code execution (`.ps1`, `.bat`, `.cmd`).

---

## 2. Linux Command Availability & Fallback Matrix

When running on Linux, E-SHELL inspects your environment before executing external commands. If a standard tool is not installed, E-SHELL automatically engages a built-in fallback:

| Intent / Feature | Primary Linux Command | Package Name | Fallback Mechanism (When Binary Is Missing) |
| :--- | :--- | :--- | :--- |
| **`disk_usage`** | `df -h` | `coreutils` | `shutil.disk_usage("/")` (reports total, used, free GB) |
| **`memory_usage`** | `free -h` | `procps` / `procps-ng` | Parses `/proc/meminfo` (`MemTotal`, `MemAvailable` / `MemFree`) |
| **`system_uptime`** | `uptime` | `procps` / `procps-ng` | Reads and formats `/proc/uptime` seconds into days/hours/mins |
| **`kernel_info`** | `uname -a` | `coreutils` | `platform.platform()` (Python standard library) |
| **`cpu_info`** | `lscpu` | `util-linux` | Parses `/proc/cpuinfo` for processor model name and core count |
| **`current_user`** | `whoami` | `coreutils` | `getpass.getuser()`, followed by `USER` or `LOGNAME` env vars |
| **`hostname`** | `hostname` | `hostname` / `coreutils` | `socket.gethostname()` |
| **`os_info`** | `lsb_release -a` | `lsb-release` | Reads `/etc/os-release`; falls back to `uname -sro` |
| **`network_info`** | `ip route` & `ip -brief address` | `iproute2` | Falls back to `ifconfig` (`net-tools`) |
| **`ip_address`** | `hostname -I` | `hostname` / `net-tools` | `ip -4 addr`; falls back to `socket.gethostbyname()` |
| **`running_processes`**| `ps aux` | `procps` / `procps-ng` | Falls back to `ps -ef` |
| **`logged_in_users`** | `who` | `coreutils` | Falls back to `w`; falls back to `getpass.getuser()` |
| **`battery_info`** | `/sys/class/power_supply` | Kernel `/sys` | Inspects `BAT*` device nodes directly without external binaries |
| **`gpu_info`** | `lspci` | `pciutils` | Detects VGA/3D display lines; warns cleanly if `lspci` is missing |
| **`fastfetch_info`** | `fastfetch` | `fastfetch` | Falls back to `neofetch`; falls back to built-in system summary |
| **`environment_info`**| Pure Python | None | Directly reads sanitized `os.environ` |
| **`shell_info`** | Pure Python | None | Directly inspects `SHELL` env var or current interpreter shell |
| **`python_version`** | Pure Python | None | Uses `platform.python_version()` |

---

## 3. Package Prerequisites by Linux Distribution

If you want the full native command outputs rather than the fallback summaries, install the recommended packages:

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install -y coreutils procps util-linux pciutils iproute2 lsb-release
```
*Optional tools:*
```bash
sudo apt install -y htop btop ncdu tree fzf fastfetch
```

### Fedora / RHEL / CentOS
```bash
sudo dnf install -y coreutils procps-ng util-linux pciutils iproute
```
*Optional tools:*
```bash
sudo dnf install -y htop btop ncdu tree fzf fastfetch
```

### Arch Linux / Manjaro
```bash
sudo pacman -Syu --needed coreutils procps-ng util-linux pciutils iproute2
```
*Optional tools:*
```bash
sudo pacman -S --needed htop btop ncdu tree fzf fastfetch
```

### Alpine Linux
```bash
apk add coreutils procps util-linux pciutils iproute2
```

---

## 4. Windows Compatibility Layer

E-SHELL includes full native support for Windows through `platforms/windows.py`. When launched on Windows, E-SHELL automatically detects the OS via `platform.system()` and activates `WindowsBackend`.

### Windows Command Mappings

| Feature | Windows Backend Implementation | Equivalent Linux Feature |
| :--- | :--- | :--- |
| **File Listing** | Native Python `os.listdir()` / `dir` | `ls` |
| **Current Directory** | `os.getcwd()` | `pwd` |
| **Disk Usage** | `shutil.disk_usage("C:\\")` / `Get-PSDrive` | `df -h` |
| **Memory Usage** | `Get-CimInstance Win32_OperatingSystem` | `free -h` |
| **Uptime** | `LastBootUpTime` via WMI/CIM | `uptime` |
| **CPU Info** | `Win32_Processor` via CIM (`Name`, `NumberOfCores`) | `lscpu` |
| **GPU Info** | `Win32_VideoController` via CIM (`Name`) | `lspci` |
| **Battery Info** | `Win32_Battery` via CIM (`EstimatedChargeRemaining`) | `/sys/class/power_supply` |
| **Network & IP** | `ipconfig` & `socket.gethostbyname_ex()` | `ip address` / `hostname -I` |
| **Process List** | `tasklist` | `ps aux` |
| **Current User** | `whoami` / `USERNAME` environment variable | `whoami` |
| **Hostname** | `hostname` / `COMPUTERNAME` environment variable | `hostname` |

### Supported Editors on Windows
* **Notepad**: Launches `notepad.exe <file>`
* **VS Code**: Launches `code <file>`
* **Sublime Text**: Launches `subl <file>`
* Command-line editors (`micro`, `vim`, `nano`) if installed and present on your Windows `PATH`.

### Supported Code Execution on Windows
Code files inside `workspace/` can be executed directly using native tools:
* **Python**: `python <file>.py`
* **PowerShell**: `powershell -ExecutionPolicy Bypass -File <file>.ps1`
* **Batch**: `cmd /c <file>.bat` or `<file>.cmd`
* **Node.js**: `node <file>.js`
* **Go / Rust / C / C++**: Supported when the respective compiler (`go`, `rustc`, `gcc`) is added to Windows `PATH`.

---

## 5. Security & Safety Invariants Across All Platforms

Regardless of whether E-SHELL runs on Linux or Windows:
1. **Directory Traversal Protection**: Relative escapes (`..`), rooted paths (`/`, `C:\`), and shell metacharacters (`|`, `&`, `;`, `$`, `` ` ``) are strictly blocked.
2. **Destructive Command Prevention**: Dangerous commands (`rm`, `rmdir`, `del`, `Format-Volume`, `sudo`, `kill`) are intercepted and rejected.
3. **Execution Sandbox**: Running and editing files are restricted exclusively to the `workspace/` subfolder.
4. **Execution Confirmation**: Interactive prompt confirmation is required before running executable code for the first time.
