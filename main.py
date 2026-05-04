"""
main.py
Entry point for ADB Device Manager.
"""

import tkinter as tk
import sys
import os

# Ensure the project directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import ADBDeviceManagerApp


def main():
    root = tk.Tk()
    root.resizable(True, True)

    # Try to set a nice app icon if available
    icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    if os.path.isfile(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    app = ADBDeviceManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
