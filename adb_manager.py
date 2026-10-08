"""
adb_manager.py
Handles ADB path detection, device listing, device info, and raw command execution.

IMPROVEMENTS:
- get_device_info() batches all 5 getprop calls into ONE adb shell invocation
- run_shell_command() correctly handles commands with spaces / quoted args
- adb_start_server() warms up the ADB daemon so first real call is fast
"""

import subprocess
import platform
import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path


def _current_platform_keys():
    """Return platform-specific resource folder names and executable name."""
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        arch_key = "windows-arm64" if "arm" in machine else "windows-x64"
        return [arch_key, "windows"], "adb.exe"

    if system == "Darwin":
        arch_key = "macos-arm64" if machine in {"arm64", "aarch64"} else "macos-x64"
        return [arch_key, "macos"], "adb"

    arch_key = "linux-arm64" if machine in {"arm64", "aarch64"} else "linux-x64"
    return [arch_key, "linux"], "adb"


def _runtime_search_roots():
    """Yield directories where a bundled or sidecar adb binary may live."""
    roots = []
    script_dir = Path(__file__).resolve().parent
    executable_dir = Path(sys.executable).resolve().parent

    roots.append(script_dir)
    roots.append(executable_dir)
    roots.append(executable_dir.parent)
    roots.append(executable_dir.parent.parent)

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        roots.insert(0, Path(sys._MEIPASS).resolve())

    # Keep order stable while removing duplicates.
    seen = set()
    ordered_roots = []
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            ordered_roots.append(root)
    return ordered_roots


def _ensure_executable(path):
    """Make sure bundled adb is executable on POSIX systems."""
    if platform.system() == "Windows":
        return

    current_mode = path.stat().st_mode
    desired_mode = current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    if desired_mode != current_mode:
        path.chmod(desired_mode)


def get_adb_path():
    """Return the adb executable path based on OS and availability."""
    platform_dirs, executable_name = _current_platform_keys()

    candidates = []
    for root in _runtime_search_roots():
        candidates.append(root / executable_name)
        for platform_dir in platform_dirs:
            candidates.append(root / "platform-tools" / platform_dir / executable_name)
            candidates.append(root / "resources" / "platform-tools" / platform_dir / executable_name)

    for candidate in candidates:
        if candidate.is_file():
            try:
                _ensure_executable(candidate)
            except OSError:
                pass
            return str(candidate)

    return shutil.which("adb")


def run_adb_command(args, timeout=30):
    """
    Run an adb command with the given argument list.
    Returns (stdout, stderr, returncode, timestamp).
    args: list of strings after 'adb', e.g. ['devices']
    """
    adb = get_adb_path()
    timestamp = datetime.now().strftime("%H:%M:%S")
    if not adb:
        return (
            "",
            "ADB not found. Install Android Platform Tools, place adb next to the app, or bundle it under resources/platform-tools.",
            -1,
            timestamp,
        )

    cmd = [adb] + args
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        return stdout, stderr, result.returncode, timestamp
    except subprocess.TimeoutExpired:
        return "", "Command timed out.", 1, timestamp
    except FileNotFoundError:
        return "", "ADB executable not found. Install Android Platform Tools or supply a bundled adb binary.", -1, timestamp
    except Exception as e:
        return "", f"Unexpected error: {e}", 1, timestamp


def run_shell_command(serial, shell_cmd, timeout=30):
    """
    Run: adb -s SERIAL shell SHELL_CMD
    shell_cmd is passed as a single shell string (not split), so quoted
    arguments and semicolons work correctly.
    Returns (stdout, stderr, returncode, timestamp).
    """
    # Pass the whole command string as one argument to `shell` so the device
    # shell interprets it — this avoids incorrect splitting on spaces.
    return run_adb_command(["-s", serial, "shell", shell_cmd], timeout=timeout)


def adb_start_server():
    """
    Warm up the ADB daemon in the background so the first device scan is fast.
    Safe to call from a thread — fire-and-forget.
    """
    run_adb_command(["start-server"], timeout=10)


def list_devices():
    """
    Run 'adb devices' and return (list of dicts, error_string).
    Each dict: {'serial': ..., 'status': ...}
    """
    stdout, stderr, code, _ = run_adb_command(["devices"])
    devices = []
    if code == -1:
        return devices, stderr
    if code != 0:
        return devices, stderr or "Unknown error running adb devices."

    lines = stdout.splitlines()
    for line in lines[1:]:          # skip "List of devices attached"
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            devices.append({"serial": parts[0].strip(), "status": parts[1].strip()})
        else:
            tokens = line.split()
            if len(tokens) >= 2:
                devices.append({"serial": tokens[0], "status": tokens[1]})

    return devices, ""


def get_device_info(serial):
    """
    Fetch all device properties in a SINGLE adb shell invocation instead of 5.
    Returns a dict with manufacturer, model, android_version, sdk, serial, fingerprint.
    """
    # Build one compound shell command with separators we can split on
    SEP = "|||"
    props = [
        "ro.product.manufacturer",
        "ro.product.model",
        "ro.build.version.release",
        "ro.build.version.sdk",
        "ro.build.fingerprint",
    ]
    # e.g. getprop ro.product.manufacturer; echo |||; getprop ro.product.model; ...
    shell_cmd = f"; echo '{SEP}'; ".join(f"getprop {p}" for p in props)

    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", shell_cmd], timeout=15
    )

    keys = ["manufacturer", "model", "android_version", "sdk", "fingerprint"]
    info = {"serial": serial}

    if code == 0 and stdout:
        parts = stdout.split(SEP)
        for i, key in enumerate(keys):
            val = parts[i].strip() if i < len(parts) else ""
            info[key] = val if val else "N/A"
    else:
        for key in keys:
            info[key] = "N/A"

    return info
