"""
Shared branding and runtime asset helpers for ADB KING.
"""

from __future__ import annotations

import sys
from pathlib import Path


APP_NAME = "ADB KING"
APP_DESCRIPTION = "Manage Android apps over USB with a faster, cleaner desktop workflow."
APP_ORGANIZATION = "ADB KING"
APP_SLUG = "adb-king"
APP_BUNDLE_ID = "com.ramascript.adbking"
DEFAULT_THEME = "Light"


def _runtime_roots():
    roots = []
    script_dir = Path(__file__).resolve().parent
    executable_dir = Path(sys.executable).resolve().parent

    roots.append(script_dir)
    roots.append(executable_dir)
    roots.append(executable_dir.parent)
    roots.append(executable_dir.parent.parent)

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        roots.insert(0, Path(sys._MEIPASS).resolve())

    seen = set()
    ordered_roots = []
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            ordered_roots.append(root)
    return ordered_roots


def _resolve_first(*relative_paths):
    for root in _runtime_roots():
        for relative_path in relative_paths:
            candidate = root / relative_path
            if candidate.is_file():
                return candidate
    return None


def resolve_icon_path():
    icon_path = _resolve_first(
        "icon.icns",
        "icon.ico",
        "icon.png",
        "resources/branding/icon.png",
    )
    return str(icon_path) if icon_path else None


def resolve_logo_path():
    logo_path = _resolve_first(
        "resources/branding/icon.png",
        "icon.png",
    )
    return str(logo_path) if logo_path else None
