"""
Build distributable desktop release assets for the current platform.

Windows:
    Creates a single-file .exe and zips it for GitHub Releases.

macOS:
    Creates an .app bundle and zips it with `ditto` so Finder metadata and
    executable permissions are preserved.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

from app_metadata import APP_BUNDLE_ID, APP_NAME

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
WORK_DIR = ROOT / "build" / "pyinstaller"
SPEC_DIR = ROOT / "build" / "spec"
RELEASE_DIR = ROOT / "release"
RESOURCES_DIR = ROOT / "resources"
PYINSTALLER_CONFIG_DIR = ROOT / ".pyinstaller-config"


def _normalized_arch():
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "x64"
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    return machine


def _platform_slug():
    system = platform.system()
    arch = _normalized_arch()
    if system == "Windows":
        return f"windows-{arch}"
    if system == "Darwin":
        return f"macos-{arch}"
    if system == "Linux":
        return f"linux-{arch}"
    raise RuntimeError(f"Unsupported platform: {system}")


def _generic_platform_slug():
    system = platform.system()
    mapping = {
        "Windows": "windows",
        "Darwin": "macos",
        "Linux": "linux",
    }
    if system not in mapping:
        raise RuntimeError(f"Unsupported platform: {system}")
    return mapping[system]


def _required_platform_files():
    if platform.system() == "Windows":
        return ["adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll"]
    return ["adb"]


def _resolve_platform_tools_dir():
    candidates = [
        RESOURCES_DIR / "platform-tools" / _platform_slug(),
        RESOURCES_DIR / "platform-tools" / _generic_platform_slug(),
    ]
    required_files = _required_platform_files()

    for candidate in candidates:
        if all((candidate / file_name).is_file() for file_name in required_files):
            return candidate

    expected = "\n".join(
        f"  - {candidate}" for candidate in candidates
    )
    required = ", ".join(required_files)
    raise RuntimeError(
        "Bundled platform-tools are missing for this build.\n"
        f"Expected one of these folders:\n{expected}\n"
        f"Required files: {required}\n"
        "See resources/platform-tools/README.md for the expected structure."
    )


def _data_arg(source, target):
    separator = ";" if platform.system() == "Windows" else ":"
    return f"{source}{separator}{target}"


def _data_args():
    args = [_data_arg(RESOURCES_DIR, "resources")]
    icon_path = ROOT / "icon.png"
    if icon_path.is_file():
        args.append(_data_arg(icon_path, "resources/branding"))
    return args


def _icon_args():
    candidates = {
        "Windows": [ROOT / "icon.ico", ROOT / "icon.png"],
        "Darwin": [ROOT / "icon.icns", ROOT / "icon.png"],
    }.get(platform.system(), [ROOT / "icon.png"])

    for candidate in candidates:
        if candidate.is_file():
            return ["--icon", str(candidate)]
    return []


def _build_pyinstaller_command():
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--windowed",
    ]

    for data_arg in _data_args():
        command.extend(["--add-data", data_arg])

    if platform.system() == "Windows":
        command.append("--onefile")
    elif platform.system() == "Darwin":
        command.extend(["--osx-bundle-identifier", APP_BUNDLE_ID])

    command.extend(_icon_args())
    command.append(str(ROOT / "main.py"))
    return command


def _zip_windows_asset(executable_path, zip_path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(executable_path, executable_path.name)


def _zip_macos_asset(app_path, zip_path):
    subprocess.run(
        [
            "ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(app_path),
            str(zip_path),
        ],
        check=True,
    )


def main():
    _resolve_platform_tools_dir()

    PYINSTALLER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)

    command = _build_pyinstaller_command()
    env = os.environ.copy()
    env.setdefault("PYINSTALLER_CONFIG_DIR", str(PYINSTALLER_CONFIG_DIR))
    print("Running:", " ".join(command))
    subprocess.run(command, check=True, cwd=ROOT, env=env)

    platform_slug = _platform_slug()
    zip_path = RELEASE_DIR / f"{APP_NAME}-{platform_slug}.zip"
    if zip_path.exists():
        zip_path.unlink()

    if platform.system() == "Windows":
        executable_path = DIST_DIR / f"{APP_NAME}.exe"
        if not executable_path.is_file():
            raise RuntimeError(f"Expected build output not found: {executable_path}")
        _zip_windows_asset(executable_path, zip_path)
    elif platform.system() == "Darwin":
        app_path = DIST_DIR / f"{APP_NAME}.app"
        if not app_path.exists():
            raise RuntimeError(f"Expected build output not found: {app_path}")
        _zip_macos_asset(app_path, zip_path)
    else:
        raise RuntimeError("Only Windows and macOS release assets are configured right now.")

    print(f"Release asset created: {zip_path}")


if __name__ == "__main__":
    main()
