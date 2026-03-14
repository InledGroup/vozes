#!/bin/bash

# Configuration
APP_ID="org.vozes.Vozes"
MANIFEST="org.vozes.Vozes.yaml"
BUILD_DIR="build-flatpak"
REPO_DIR="repo-flatpak"

# Check if flatpak-builder is installed
if ! command -v flatpak-builder &> /dev/null; then
    echo "Error: flatpak-builder is not installed. Please install it (e.g., sudo apt install flatpak-builder)"
    exit 1
fi

# Ensure runtimes are installed
echo "Checking for GNOME 45 runtimes..."
flatpak install -y flathub org.gnome.Platform//45 org.gnome.Sdk//45

# Clean previous builds
echo "Cleaning previous build directories..."
rm -rf "$BUILD_DIR" "$REPO_DIR"

# Build the flatpak
echo "Building $APP_ID..."
flatpak-builder --force-clean --user --install --ccache "$BUILD_DIR" "$MANIFEST"

if [ $? -eq 0 ]; then
    echo "------------------------------------------------"
    echo "Build successful! Running $APP_ID..."
    echo "------------------------------------------------"
    flatpak run "$APP_ID"
else
    echo "------------------------------------------------"
    echo "Build failed! Please check the output above."
    echo "------------------------------------------------"
    exit 1
fi
