"""
adb_manager.py
Handles ADB path detection, device listing, device info, and raw command execution.
"""

import subprocess
import platform
import os
import shutil
from datetime import datetime


def get_adb_path():
    """Return the adb executable path based on OS and availability."""
    # 1. Check for bundled adb in the project folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if platform.system() == "Windows":
        bundled = os.path.join(script_dir, "adb.exe")
    else:
        bundled = os.path.join(script_dir, "adb")

    if os.path.isfile(bundled):
        return bundled

    # 2. Check system PATH
    system_adb = shutil.which("adb")
    if system_adb:
        return system_adb

    return None


def run_adb_command(args, timeout=30):
    """
    Run an adb command with the given argument list.
    Returns (stdout, stderr, returncode, timestamp).
    args: list of strings after 'adb', e.g. ['devices']
    """
    adb = get_adb_path()
    if not adb:
        return (
            "",
            "ADB not found. Please install Android Platform Tools or place adb inside the project folder.",
            -1,
            datetime.now().strftime("%H:%M:%S"),
        )

    cmd = [adb] + args
    timestamp = datetime.now().strftime("%H:%M:%S")
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
        return (
            "",
            "ADB executable not found. Please install Android Platform Tools.",
            -1,
            timestamp,
        )
    except Exception as e:
        return "", f"Unexpected error: {e}", 1, timestamp


def run_shell_command(serial, shell_cmd, timeout=30):
    """
    Run: adb -s SERIAL shell SHELL_CMD
    Returns (stdout, stderr, returncode, timestamp).
    """
    return run_adb_command(["-s", serial, "shell"] + shell_cmd.split(), timeout=timeout)


def list_devices():
    """
    Run 'adb devices' and return list of dicts:
    [{'serial': ..., 'status': ...}, ...]
    """
    stdout, stderr, code, _ = run_adb_command(["devices"])
    devices = []
    if code != 0 and code != -1:
        return devices, stderr or "Unknown error running adb devices."
    if code == -1:
        return devices, stderr

    lines = stdout.splitlines()
    # First line is "List of devices attached"
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            serial = parts[0].strip()
            status = parts[1].strip()
            devices.append({"serial": serial, "status": status})
        elif len(parts) == 1 and parts[0]:
            # edge case: sometimes no tab
            tokens = line.split()
            if len(tokens) >= 2:
                devices.append({"serial": tokens[0], "status": tokens[1]})

    return devices, ""


def get_device_info(serial):
    """
    Fetch device properties for the given serial.
    Returns a dict with manufacturer, model, android_version, sdk, serial, fingerprint.
    """
    props = {
        "manufacturer": "ro.product.manufacturer",
        "model": "ro.product.model",
        "android_version": "ro.build.version.release",
        "sdk": "ro.build.version.sdk",
        "fingerprint": "ro.build.fingerprint",
    }

    info = {"serial": serial}
    for key, prop in props.items():
        stdout, stderr, code, _ = run_adb_command(
            ["-s", serial, "shell", "getprop", prop]
        )
        info[key] = stdout.strip() if code == 0 and stdout.strip() else "N/A"

    return info
