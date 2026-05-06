# ADB Device Manager

A PySide6 desktop app for managing Android apps over ADB without typing terminal commands.

## What It Does

- Detects ADB from a bundled release payload, a sidecar platform-tools folder, or your system `PATH`
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

## Source Run Requirements

- Python 3.8+
- PySide6
- ADB available in one of these ways:
  - installed on your system `PATH`
  - placed next to the source as `adb` or `adb.exe`
  - placed in `resources/platform-tools/...` using the structure shown below

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

## Bundling ADB Inside the App

If you want end users to download the app and run it without installing ADB themselves, the app can look for bundled platform-tools in these folders:

```text
resources/
└── platform-tools/
    ├── windows-x64/
    │   ├── adb.exe
    │   ├── AdbWinApi.dll
    │   └── AdbWinUsbApi.dll
    ├── macos-arm64/
    │   └── adb
    └── macos-x64/
        └── adb
```

Fallback folders are also supported:

```text
resources/platform-tools/windows/
resources/platform-tools/macos/
```

### Important Licensing Note

Before you publish a public GitHub release that bundles ADB, review the current Android SDK terms carefully.

The Android SDK terms page currently says you may not "redistribute" the SDK except as expressly permitted:

- Android SDK terms: [developer.android.com/studio/terms](https://developer.android.com/studio/terms)
- Platform-Tools downloads: [developer.android.com/studio/releases/platform-tools](https://developer.android.com/studio/releases/platform-tools)

Practical takeaway:

1. Do not blindly upload Google's Platform-Tools binaries to a public GitHub release.
2. The safer paths are:
   - ask users to install Platform-Tools separately
   - ship your own redistributable `adb` build after legal review
   - build `adb` from AOSP source and confirm your distribution obligations

If you are distributing only inside a private team, your legal review threshold may be different, but you should still verify it yourself.

## Building Release Assets Locally

This repo now includes a release builder script for the current platform.

Install build dependencies:

```bash
pip install -r requirements.txt -r requirements-build.txt
```

Place the bundled platform-tools files in `resources/platform-tools/...`, then run:

```bash
python build_release.py
```

Output:

- Windows: `release/ADB-KING-windows-x64.zip`
- macOS Intel: `release/ADB-KING-macos-x64.zip`
- macOS Apple Silicon: `release/ADB-KING-macos-arm64.zip`

Notes:

- You must build Windows on Windows.
- You must build macOS on macOS.
- PyInstaller does not replace Apple code signing or notarization.

## Exact GitHub Release Flow

This repo includes `.github/workflows/release.yml`.

That workflow:

1. Builds Windows x64 on `windows-latest`
2. Builds macOS Intel on `macos-15-intel`
3. Builds macOS Apple Silicon on `macos-latest`
4. Uploads the artifacts from each build job
5. Creates a GitHub Release from the pushed tag and attaches the ZIP files

### One-Time Setup

1. Create a GitHub repository and push this project.
2. Make sure `resources/platform-tools/...` contains the platform files you intend to package.
3. Make sure GitHub Actions is enabled for the repository.

If the local folder is not connected to GitHub yet, you can do it with GitHub CLI:

```bash
gh repo create ADB-KING --public --source=. --remote=origin --push
```

### Releasing a Version

1. Commit your changes.
2. Create a version tag.
3. Push the branch and the tag.

Example:

```bash
git add .
git commit -m "Prepare release v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

Once the tag is pushed, GitHub Actions will build the desktop artifacts and publish a release automatically.

### Manual GitHub Release Alternative

If you do not want automation yet, you can build locally and upload the ZIP files yourself:

1. Run `python build_release.py` on each platform you support.
2. Open your repository on GitHub.
3. Go to `Releases`.
4. Click `Draft a new release`.
5. Choose tag `vX.Y.Z`.
6. Upload the ZIP files from the `release/` folder.
7. Publish the release.

GitHub release docs:

- About releases: [docs.github.com/repositories/releasing-projects-on-github/about-releases](https://docs.github.com/repositories/releasing-projects-on-github/about-releases)
- Managing releases: [docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
- `gh release create`: [cli.github.com/manual/gh_release_create](https://cli.github.com/manual/gh_release_create)

## macOS Distribution Reality Check

If you want Mac users to open the app without Gatekeeper warnings, you should plan to:

1. Sign the app with a Developer ID certificate
2. Notarize it with Apple's notary service

Apple docs:

- Developer ID: [developer.apple.com/support/developer-id](https://developer.apple.com/support/developer-id/)
- Notarization overview: [developer.apple.com/documentation/security/notarizing-macos-software-before-distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)

Without this, the app may still run, but users can see the "developer cannot be verified" warning.

## Enable USB Debugging

1. Open `Settings > About Phone`
2. Tap `Build Number` 7 times
3. Open `Settings > Developer Options`
4. Turn on `USB Debugging`
5. Connect the phone with a USB cable
6. Accept the USB debugging authorization prompt on the phone

## Project Structure

```text
ADB-KING/
├── .github/workflows/release.yml
├── adb_manager.py
├── app_manager.py
├── build_release.py
├── main.py
├── requirements.txt
├── requirements-build.txt
├── resources/platform-tools/README.md
├── ui.py
└── README.md
```

## Safety Warning

- Disabling system apps can break core phone features
- Uninstalling a package for the current user may hide critical apps for that user profile
- Always review the package type before disabling or uninstalling
- This app does not require root

## Troubleshooting

- `ADB not found`
  Put redistributable platform-tools files in `resources/platform-tools/...`, place `adb` next to the app, or install ADB on your `PATH`
- `Device unauthorized`
  Unlock the phone and accept the USB debugging prompt
- `Device offline`
  Reconnect the cable, unlock the phone, and refresh devices
- Empty package list
  Select a valid device with status `device`, then click `Refresh Apps`
- macOS app will not open
  Sign and notarize the app, or use Finder's secondary open flow for unsigned apps
