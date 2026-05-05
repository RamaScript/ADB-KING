"""
app_manager.py
Handles all package/app management operations via ADB.

IMPROVEMENTS:
- classify_packages() now runs ALL 4 pm list packages calls in a single
  adb shell invocation using semicolons, cutting round-trips from 4 → 1.
  This is the single biggest speed improvement (saves ~3-9 seconds).
"""

from adb_manager import run_adb_command


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_packages(block):
    """Parse a pm list packages output block into a set of package names."""
    packages = set()
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            pkg = line[len("package:"):].strip()
            if pkg:
                packages.add(pkg)
    return packages


# ── Batch classify (fast path) ────────────────────────────────────────────────

_SEP = "<<<SPLIT>>>"

def classify_packages(serial):
    """
    Classify all installed packages in ONE adb shell round-trip.

    Previously this made 4 separate ADB calls (all, -3, -s, -d).
    Now it issues a single compound shell command separated by a known
    sentinel, then splits the output.  Typical speedup: 3-4× faster.

    Returns (list of dicts, error_string).
    Each dict: {'package': ..., 'type': 'User'/'System'/'Unknown', 'status': 'Enabled'/'Disabled'}
    """
    shell_cmd = (
        f"pm list packages"
        f"; echo '{_SEP}'"
        f"; pm list packages -3"
        f"; echo '{_SEP}'"
        f"; pm list packages -s"
        f"; echo '{_SEP}'"
        f"; pm list packages -d"
    )

    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", shell_cmd], timeout=60
    )

    if code != 0:
        return [], stderr or "Failed to list packages."

    parts = stdout.split(_SEP)
    if len(parts) < 4:
        # Fallback: device may not support separator echo — use slow path
        return _classify_packages_slow(serial)

    all_pkgs      = _parse_packages(parts[0])
    user_pkgs     = _parse_packages(parts[1])
    system_pkgs   = _parse_packages(parts[2])
    disabled_pkgs = _parse_packages(parts[3])

    result = []
    for pkg in sorted(all_pkgs):
        if pkg in user_pkgs:
            pkg_type = "User"
        elif pkg in system_pkgs:
            pkg_type = "System"
        else:
            pkg_type = "Unknown"
        status = "Disabled" if pkg in disabled_pkgs else "Enabled"
        result.append({"package": pkg, "type": pkg_type, "status": status})

    error = stderr if stderr else ""
    return result, error


def _classify_packages_slow(serial):
    """Fallback: 4 separate ADB calls (original approach)."""
    all_pkgs,      err1 = list_all_packages(serial)
    user_pkgs,     err2 = list_user_packages(serial)
    system_pkgs,   err3 = list_system_packages(serial)
    disabled_pkgs, err4 = list_disabled_packages(serial)

    error = err1 or err2 or err3 or err4
    result = []
    for pkg in sorted(all_pkgs):
        if pkg in user_pkgs:
            pkg_type = "User"
        elif pkg in system_pkgs:
            pkg_type = "System"
        else:
            pkg_type = "Unknown"
        status = "Disabled" if pkg in disabled_pkgs else "Enabled"
        result.append({"package": pkg, "type": pkg_type, "status": status})
    return result, error


# ── Individual list functions (kept for direct use / fallback) ────────────────

def list_all_packages(serial):
    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", "pm", "list", "packages"]
    )
    return (_parse_packages(stdout), "") if code == 0 else (set(), stderr)


def list_user_packages(serial):
    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", "pm", "list", "packages", "-3"]
    )
    return (_parse_packages(stdout), "") if code == 0 else (set(), stderr)


def list_system_packages(serial):
    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", "pm", "list", "packages", "-s"]
    )
    return (_parse_packages(stdout), "") if code == 0 else (set(), stderr)


def list_disabled_packages(serial):
    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", "pm", "list", "packages", "-d"]
    )
    return (_parse_packages(stdout), "") if code == 0 else (set(), stderr)


def compute_enabled_packages(all_pkgs, disabled_pkgs):
    return all_pkgs - disabled_pkgs


# ── App actions ───────────────────────────────────────────────────────────────

def disable_package(serial, package_name):
    return run_adb_command(
        ["-s", serial, "shell", "pm", "disable-user", "--user", "0", package_name]
    )


def enable_package(serial, package_name):
    return run_adb_command(
        ["-s", serial, "shell", "pm", "enable", package_name]
    )


def uninstall_package_for_user(serial, package_name):
    return run_adb_command(
        ["-s", serial, "shell", "pm", "uninstall", "--user", "0", package_name]
    )


def open_app_info(serial, package_name):
    return run_adb_command(
        [
            "-s", serial, "shell", "am", "start",
            "-a", "android.settings.APPLICATION_DETAILS_SETTINGS",
            "-d", f"package:{package_name}",
        ]
    )