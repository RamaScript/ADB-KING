# Bundled Platform-Tools Layout

If you want packaged builds to run without the end user installing ADB separately,
place your redistributable platform-tools files in one of these folders:

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

Generic fallback folders are also supported:

```text
resources/platform-tools/windows/
resources/platform-tools/macos/
```

Important:

- The app is already coded to look for these bundled files at runtime.
- Public redistribution of Google's Android SDK Platform-Tools may require legal review.
- Read the release section in the project README before uploading public binaries to GitHub.
