"""
main.py
PySide6 entry point for ADB Device Manager.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication

        from ui import ADBDeviceManagerApp
    except ImportError:
        print("PySide6 is not installed. Install dependencies with: pip install -r requirements.txt")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("ADB Device Manager")
    app.setOrganizationName("ADB Device Manager")

    window = ADBDeviceManagerApp()

    icon_candidates = [
        os.path.join(os.path.dirname(__file__), "icon.icns"),
        os.path.join(os.path.dirname(__file__), "icon.ico"),
        os.path.join(os.path.dirname(__file__), "icon.png"),
    ]
    for icon_path in icon_candidates:
        if os.path.isfile(icon_path):
            window.setWindowIcon(QIcon(icon_path))
            app.setWindowIcon(QIcon(icon_path))
            break

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
