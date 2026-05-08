#!/usr/bin/env bash
set -euo pipefail

APP_PATH="${1:?app path is required}"
ZIP_PATH="${2:?zip path is required}"
IDENTITY="${APPLE_DEVELOPER_ID_APP_SIGNING_IDENTITY:?missing APPLE_DEVELOPER_ID_APP_SIGNING_IDENTITY}"
CERT_BASE64="${APPLE_DEVELOPER_ID_APP_CERT:?missing APPLE_DEVELOPER_ID_APP_CERT}"
CERT_PASSWORD="${APPLE_DEVELOPER_ID_APP_CERT_PASSWORD:?missing APPLE_DEVELOPER_ID_APP_CERT_PASSWORD}"
APPLE_ID="${APPLE_NOTARY_APPLE_ID:?missing APPLE_NOTARY_APPLE_ID}"
TEAM_ID="${APPLE_NOTARY_TEAM_ID:?missing APPLE_NOTARY_TEAM_ID}"
APP_PASSWORD="${APPLE_NOTARY_APP_PASSWORD:?missing APPLE_NOTARY_APP_PASSWORD}"

KEYCHAIN_PASSWORD="$(uuidgen)"
KEYCHAIN_PATH="${RUNNER_TEMP}/adb-king-signing.keychain-db"
CERT_PATH="${RUNNER_TEMP}/developer-id.p12"

python3 - <<'PY' "$CERT_BASE64" "$CERT_PATH"
import base64
import pathlib
import sys

payload = sys.argv[1]
target = pathlib.Path(sys.argv[2])
target.write_bytes(base64.b64decode(payload))
PY

security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
security set-keychain-settings -lut 21600 "$KEYCHAIN_PATH"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
security import "$CERT_PATH" -k "$KEYCHAIN_PATH" -P "$CERT_PASSWORD" -T /usr/bin/codesign -T /usr/bin/security
security list-keychains -d user -s "$KEYCHAIN_PATH"
security default-keychain -d user -s "$KEYCHAIN_PATH"
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"

codesign --force --deep --options runtime --sign "$IDENTITY" "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
xcrun notarytool submit "$ZIP_PATH" --apple-id "$APPLE_ID" --team-id "$TEAM_ID" --password "$APP_PASSWORD" --wait
xcrun stapler staple "$APP_PATH"

rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
spctl --assess --type execute --verbose "$APP_PATH"
