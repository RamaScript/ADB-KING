# ADB Device Manager

A clean, cross-platform desktop GUI tool for managing Android apps over ADB (USB) — no terminal commands needed.

---

## What It Does

- Connects to one or more Android devices via USB
- Lists all installed apps (user, system, enabled, disabled)
- Live search and filter
- Enable / Disable / Uninstall apps per user — **no root required**
- Open App Info on device
- Copy package names to clipboard
- Export package lists as TXT or CSV
- Run custom ADB shell commands
- Displays device info: manufacturer, model, Android version, SDK, serial
- Full command output log with timestamps

---

## Requirements

- **Python 3.8+**
- **ADB (Android Debug Bridge)** installed and on your system PATH
- A USB cable and an Android device with USB Debugging enabled

---

## How to Enable USB Debugging on Your Phone

1. Go to **Settings → About Phone**
2. Tap **Build Number** 7 times to unlock Developer Options
3. Go to **Settings → Developer Options**
4. Enable **USB Debugging**
5. Connect your phone to your PC with a USB cable
6. When prompted on the phone, tap **Allow** to authorize your computer

---

## How to Install ADB

### Windows
1. Download [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. Extract the ZIP
3. Add the folder to your system PATH, **or** place `adb.exe` directly in the `adb_device_manager/` folder

### macOS
Using Homebrew:
```bash
brew install android-platform-tools
```

### Linux
```bash
sudo apt install adb
# or
sudo pacman -S android-tools
```

Verify ADB is installed:
```bash
adb version
```

---

## How to Run

```bash
cd adb_device_manager
python main.py
```

---

## How to Package as a Standalone Executable (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

The executable will be in the `dist/` folder.

> **Note for macOS**: You may need `--target-architecture x86_64` on Apple Silicon for compatibility.

---

## Project Structure

```
adb_device_manager/
├── main.py          # Entry point
├── adb_manager.py   # ADB path detection, device listing, info, raw commands
├── app_manager.py   # Package listing, enable, disable, uninstall, open app info
├── ui.py            # Full Tkinter GUI
├── requirements.txt # No external dependencies
└── README.md        # This file
```

---

## ⚠️ Safety Warning

- **Disabling system apps** can break core phone functionality (dialer, launcher, settings).
- Use the "System Apps" filter to identify system packages before acting.
- The app will always ask for confirmation before disabling or uninstalling system apps.
- **Uninstall for current user** removes the app for the active user only; it can be re-enabled via factory reset or by using `pm install-existing <package>`.
- This app does **not** require root. All operations use standard ADB user-space commands.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "ADB not found" | Install Platform Tools or place `adb` in the project folder |
| "Device unauthorized" | Accept the USB debugging dialog on your phone |
| "No device connected" | Check USB cable, enable USB debugging, try a different port |
| App list is empty | Tap Refresh Apps; ensure device status is "device" not "offline" |
| Commands time out | Unlock the phone screen; check USB connection |

---

## License

MIT — free to use and modify.
