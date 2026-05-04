"""
app_manager.py
Handles all package/app management operations via ADB.
"""

from adb_manager import run_adb_command


def _parse_packages(stdout):
    """Parse pm list packages output into a set of package names."""
    packages = set()
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            pkg = line[len("package:"):].strip()
            if pkg:
                packages.add(pkg)
    return packages


def list_all_packages(serial):
    """Return (set of all package names, stderr)."""
    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", "pm", "list", "packages"]
    )
    if code != 0:
        return set(), stderr
    return _parse_packages(stdout), ""


def list_user_packages(serial):
    """Return (set of user/3rd-party package names, stderr)."""
    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", "pm", "list", "packages", "-3"]
    )
    if code != 0:
        return set(), stderr
    return _parse_packages(stdout), ""


def list_system_packages(serial):
    """Return (set of system package names, stderr)."""
    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", "pm", "list", "packages", "-s"]
    )
    if code != 0:
        return set(), stderr
    return _parse_packages(stdout), ""


def list_disabled_packages(serial):
    """Return (set of disabled package names, stderr)."""
    stdout, stderr, code, _ = run_adb_command(
        ["-s", serial, "shell", "pm", "list", "packages", "-d"]
    )
    if code != 0:
        return set(), stderr
    return _parse_packages(stdout), ""


def compute_enabled_packages(all_pkgs, disabled_pkgs):
    """Enabled = all - disabled."""
    return all_pkgs - disabled_pkgs


def classify_packages(serial):
    """
    Return list of dicts:
    [{'package': ..., 'type': 'User'/'System'/'Unknown', 'status': 'Enabled'/'Disabled'}, ...]
    plus an error string.
    """
    all_pkgs, err1 = list_all_packages(serial)
    user_pkgs, err2 = list_user_packages(serial)
    system_pkgs, err3 = list_system_packages(serial)
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


def disable_package(serial, package_name):
    """
    Disable a package for user 0.
    Returns (stdout, stderr, returncode, timestamp).
    """
    return run_adb_command(
        ["-s", serial, "shell", "pm", "disable-user", "--user", "0", package_name]
    )


def enable_package(serial, package_name):
    """
    Enable a package.
    Returns (stdout, stderr, returncode, timestamp).
    """
    return run_adb_command(
        ["-s", serial, "shell", "pm", "enable", package_name]
    )


def uninstall_package_for_user(serial, package_name):
    """
    Uninstall a package for user 0 (non-root).
    Returns (stdout, stderr, returncode, timestamp).
    """
    return run_adb_command(
        ["-s", serial, "shell", "pm", "uninstall", "--user", "0", package_name]
    )


def open_app_info(serial, package_name):
    """
    Open the App Info page on the connected device.
    Returns (stdout, stderr, returncode, timestamp).
    """
    return run_adb_command(
        [
            "-s", serial, "shell", "am", "start",
            "-a", "android.settings.APPLICATION_DETAILS_SETTINGS",
            "-d", f"package:{package_name}",
        ]
    )
