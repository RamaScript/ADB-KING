# ADB Device Manager

A clean PySide6 desktop app for managing Android apps over ADB without typing terminal commands.

## What It Does

- Detects ADB from your system PATH or from the project folder
- Lists connected Android devices and their connection state
- Shows device details like manufacturer, model, Android version, SDK, serial, and fingerprint
- Lists installed apps by category: all, user, system, enabled, and disabled
- Lets you search package names live
- Enables, disables, and uninstalls apps for the current user
- Opens Android app info pages directly on the device
- Runs custom ADB shell commands for advanced users
- Exports the visible package list to CSV or TXT
- Keeps the UI responsive with background worker threads
- Supports light and dark themes

## Requirements

- Python 3.8+
- PySide6
- ADB installed and available on your system PATH, or an `adb` binary placed in the project folder
- An Android device with USB debugging enabled

## Enable USB Debugging

1. Open `Settings > About Phone`
2. Tap `Build Number` 7 times
3. Open `Settings > Developer Options`
4. Turn on `USB Debugging`
5. Connect the phone with a USB cable
6. Accept the USB debugging authorization prompt on the phone

## Install ADB

### Windows

1. Download [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. Extract the ZIP
3. Add the folder to your PATH, or place `adb.exe` in this project folder

### macOS

```bash
brew install android-platform-tools
```

### Linux

```bash
sudo apt install adb
```

Verify installation:

```bash
adb version
```

## Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Run the App

```bash
python main.py
```

## Package with PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

## Project Structure

```text
ADB-KING/
├── main.py
├── ui.py
├── adb_manager.py
├── app_manager.py
├── requirements.txt
└── README.md
```

## Safety Warning

- Disabling system apps can break core phone features
- Uninstalling a package for the current user may hide critical apps for that user profile
- Always review the package type before disabling or uninstalling
- This app does not require root

## Troubleshooting

- `ADB not found`
  Install Android Platform Tools or place the `adb` binary in the project folder
- `Device unauthorized`
  Unlock the phone and accept the USB debugging prompt
- `Device offline`
  Reconnect the cable, unlock the phone, and refresh devices
- Empty package list
  Select a valid device with status `device`, then click `Refresh Apps`
- App does not launch
  Install PySide6 with `pip install -r requirements.txt`
