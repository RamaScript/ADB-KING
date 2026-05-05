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
from datetime import datetime


def get_adb_path():
    """Return the adb executable path based on OS and availability."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if platform.system() == "Windows":
        bundled = os.path.join(script_dir, "adb.exe")
    else:
        bundled = os.path.join(script_dir, "adb")

    if os.path.isfile(bundled):
        return bundled

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
            "ADB not found. Please install Android Platform Tools or place adb inside the project folder.",
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
        return "", "ADB executable not found. Please install Android Platform Tools.", -1, timestamp
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