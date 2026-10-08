"""
main.py
PySide6 entry point for ADB KING.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_metadata import APP_NAME, APP_ORGANIZATION, resolve_icon_path


def main():
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication

        from ui import ADBKingApp
    except ImportError:
        print("PySide6 is not installed. Install dependencies with: pip install -r requirements.txt")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_ORGANIZATION)

    window = ADBKingApp()

    icon_path = resolve_icon_path()
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))
        app.setWindowIcon(QIcon(icon_path))

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
