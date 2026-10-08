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

    # If missing (e.g. clean CI checkout), attempt to auto-fetch platform-tools
    target_dir = RESOURCES_DIR / "platform-tools" / _generic_platform_slug()
    try:
        import urllib.request
        import zipfile
        import io
        print(f"Platform-tools missing in {target_dir}. Attempting to download for {_platform_slug()}...")
        urls = {
            "Windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
            "Darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
            "Linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
        }
        url = urls.get(platform.system())
        if url:
            target_dir.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for member in z.infolist():
                    if member.filename.startswith("platform-tools/"):
                        subpath = member.filename[len("platform-tools/"):]
                        if not subpath:
                            continue
                        dest = target_dir / subpath
                        if member.is_dir():
                            dest.mkdir(parents=True, exist_ok=True)
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(z.read(member.filename))
            print(f"Successfully downloaded platform-tools into {target_dir}")
            return target_dir
    except Exception as e:
        print(f"Warning: Could not auto-download platform-tools: {e}")

    for candidate in candidates:
        if all((candidate / file_name).is_file() for file_name in required_files):
            return candidate

    print("Note: Packaging without bundled platform-tools (app will discover system ADB).")
    return None


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
