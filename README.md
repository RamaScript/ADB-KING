<div align="center">

# 👑 ADB KING

**A powerful, modern desktop GUI to manage Android apps over ADB — built for developers and power users.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-green.svg)](https://pypi.org/project/PySide6/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

<p align="center">
  No terminal commands needed. Connect your phone via USB or Wi-Fi and manage packages with one click.
</p>

</div>

---

## 💡 Why ADB KING? (The Problem It Solves)

If you've ever done Android app development in **Android Studio**, you’ve almost certainly encountered this nightmare scenario:

### The Problem: The "Ghost App" & Play Store Conflict
1. You install and debug a development build of an app onto your personal phone directly from **Android Studio** via USB debugging.
2. The app is also published on the **Google Play Store**.
3. Later on, you want to test or download the official production release from Google Play Store.
4. **Google Play Store fails with an error** (such as *"Can't install app"* or error `-505` / signature mismatch) because your phone still has artifacts, cached records, or leftover debug signatures from the development install.
5. You try to fix it by long-pressing the app icon on your phone and tapping **Uninstall**.
6. **Even after normal uninstall, Play Store STILL gives the same error!**  
   Why? Because on multi-user Android systems (or modern OEM setups), standard uninstallation often only uninstalls the app for one profile, leaving remnants in `/data/app` or keeping the package entry registered in the Package Manager with cached debug certificates.
7. To completely fix it and let Google Play Store install the app again, you are forced to plug your phone into your PC/Mac, open a terminal, configure ADB, look up package names, and run command-line commands like:
   ```bash
   adb uninstall <package_name>
   adb uninstall --user 0 <package_name>
   ```

### The Solution: ADB KING 👑
**ADB KING eliminates the terminal hassle.**  
Plug your phone into your computer, launch ADB KING, search for the troublesome package, and click **Uninstall** (or **Clear Data** / **Force Stop** / **Disable**). ADB KING completely purges the ghost package remnants across ADB cleanly in seconds, allowing you to install or update smoothly from the Google Play Store again.

Beyond fixing Play Store conflicts, ADB KING also doubles as a sleek, safe tool to debloat carrier/OEM junk, freeze background bloatware, and inspect device internals without root.

---

## ✨ Features

- 🔍 **Fix Ghost/Stuck App Remnants:** Completely remove development and corrupted packages so Google Play Store updates and installations work again.
- ⚡ **Zero ADB Terminal Hassle:** Auto-detects ADB from your system `PATH`, local sidecar folders, or bundled resources.
- 📱 **Real-time Device Diagnostics:** Displays device status, manufacturer, model, Android version, API level, serial number, and build fingerprint.
- 🗂️ **Categorized Package Browser:** Filter apps instantly into **All**, **User Apps**, **System Apps**, **Enabled**, and **Disabled**.
- 🔎 **Live Instant Search:** Search through hundreds of packages instantly by name.
- 🛠️ **Full Package Controls:**
  - **Uninstall / Debloat:** Clean removal via ADB.
  - **Enable / Freeze / Disable:** Disable background bloatware without root.
  - **Clear Data & Cache:** Reset app storage instantly.
  - **Force Stop:** Kill hanging app processes.
  - **Open App Info:** Launches the native Android settings page on your device screen.
- 💻 **Integrated ADB Shell Console:** Run arbitrary ADB shell commands and view output directly inside the UI.
- 📤 **Export Lists:** Save and export the visible package list to **TXT** or **CSV** for auditing or backup.
- 🎨 **Modern Clean UI:** Built with PySide6 (Qt) featuring smooth background worker threads (no UI freezes) and **Light / Dark** theme toggles.

---

## 🚀 Getting Started

### Prerequisites

1. **Python 3.8+** installed on your machine.
2. **USB Debugging enabled** on your Android device:
   - Go to `Settings` > `About phone`.
   - Tap `Build number` **7 times** to unlock Developer Options.
   - Go to `Settings` > `System` (or `Additional Settings`) > `Developer options`.
   - Toggle on **USB debugging**.
   - Connect your phone to your computer with a USB cable and tap **Allow / OK** on the phone prompt (*"Allow USB debugging?"*).

---

### Installation & Running from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/RamaScript/ADB-KING.git
   cd ADB-KING
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the app:**
   ```bash
   python main.py
   ```

---

## 📦 Standalone Releases & Packaging

You can package **ADB KING** into a standalone executable (`.exe` on Windows, `.app` / `.zip` on macOS):

1. Install packaging dependencies:
   ```bash
   pip install -r requirements.txt -r requirements-build.txt
   ```

2. Build for your current platform:
   ```bash
   python build_release.py
   ```
   Built artifacts will be placed in the `release/` directory.

### Bundling Platform-Tools (ADB)

The application automatically resolves `adb` in this order:
1. Bundled application resources (`resources/platform-tools/<os>-<arch>/`)
2. Local sidecar executable next to the app
3. System `PATH` (if you already have Android SDK / Platform-Tools installed)

To bundle ADB directly into standalone builds, see the layout guide in [`resources/platform-tools/README.md`](resources/platform-tools/README.md).

---

## 🧭 Project Architecture

```text
ADB-KING/
├── main.py                  # Application entry point & Qt app lifecycle
├── ui.py                    # PySide6 modern UI (tables, filters, shell runner, worker threads)
├── adb_manager.py           # ADB detection, device polling, batched getprop queries
├── app_manager.py           # App package classification, enable/disable/uninstall actions
├── app_metadata.py          # App branding, names, versioning, and icon resolvers
├── build_release.py         # PyInstaller multi-platform release packager
├── requirements.txt         # Runtime dependencies (PySide6)
├── requirements-build.txt   # Build dependencies (PyInstaller)
├── resources/               # Assets, icons, and platform-tools layout
└── scripts/                 # Utility scripts (e.g., macOS code signing & notarization)
```

---

## ⚠️ Safety & Disclaimer

- **No Root Required:** ADB KING operates using standard ADB commands (`pm`, `am`) and does not require rooting your phone.
- **System Apps:** Disabling or uninstalling core system packages (e.g., system UI, phone services) may cause your device to misbehave. Exercise caution when modifying system apps.
- **User Profile Removals:** Uninstallation of pre-installed apps is performed for the primary user profile (`pm uninstall -k --user 0`).

---

## 🤝 Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
