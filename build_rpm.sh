#!/bin/bash
set -e

# Configuration
APP_NAME="vozes"
# Extract version from build_deb.sh to maintain a single source of truth
if [ -z "$VERSION" ] && [ -f "build_deb.sh" ]; then
    VERSION=$(grep -oP 'VERSION="\$\{VERSION:-\K[^}]+' build_deb.sh || echo "")
fi
VERSION="${VERSION:-1.6.0}"
# Detect architecture
if command -v dpkg >/dev/null 2>&1; then
    ARCH="${ARCH:-$(dpkg --print-architecture)}"
else
    UNAME_M=$(uname -m)
    if [ "$UNAME_M" = "x86_64" ]; then
        ARCH="${ARCH:-amd64}"
    elif [ "$UNAME_M" = "aarch64" ] || [ "$UNAME_M" = "arm64" ]; then
        ARCH="${ARCH:-arm64}"
    else
        ARCH="${ARCH:-$UNAME_M}"
    fi
fi
DEB_NAME="${APP_NAME}_${VERSION}_${ARCH}"
DEB_FILE="${DEB_NAME}.deb"

# Ensure deb package exists
if [ ! -f "$DEB_FILE" ]; then
    echo "Debian package not found. Building it first..."
    ./build_deb.sh
fi

echo "Converting $DEB_FILE to RPM..."

if command -v alien >/dev/null; then
    # Convert to rpm, keeping the version and trying to convert scripts
    # Using fakeroot if not root, or sudo if running as a user
    if [ "$(id -u)" -ne 0 ] && command -v fakeroot >/dev/null; then
        fakeroot alien --to-rpm --scripts --keep-version "$DEB_FILE"
    else
        sudo alien --to-rpm --scripts --keep-version "$DEB_FILE"
    fi
    
    # alien generates a package like: vozes-1.6.0-2.x86_64.rpm
    RPM_FILE=$(ls ${APP_NAME}-${VERSION}-*.rpm 2>/dev/null | head -n 1)
    if [ -n "$RPM_FILE" ]; then
        echo "RPM package created successfully: $RPM_FILE"
    else
        echo "Error: RPM package not found after alien conversion."
        exit 1
    fi
else
    echo "Error: 'alien' is not installed. Please run 'sudo apt install alien' to convert packages."
    exit 1
fi
