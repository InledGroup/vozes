#!/bin/bash
set -e

# Configuration
APP_NAME="vozes"
VERSION="1.1.0"
# Detect architecture automatically
ARCH=$(dpkg --print-architecture)
DEB_NAME="${APP_NAME}_${VERSION}_${ARCH}"
BUILD_DIR="$(pwd)/$DEB_NAME"

echo "----------------------------------------------------------"
echo "Building Debian package for: $ARCH ($DEB_NAME)"
echo "----------------------------------------------------------"

# 1. Clean previous builds
rm -rf "$BUILD_DIR"
rm -f "${DEB_NAME}.deb"

# 2. Create directory structure
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/vozes/src"
mkdir -p "$BUILD_DIR/usr/share/vozes/bin"
mkdir -p "$BUILD_DIR/usr/share/vozes/models"
mkdir -p "$BUILD_DIR/usr/share/vozes/data"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$BUILD_DIR/etc/udev/rules.d"

# 3. Compile/Ensure Whisper binary exists
WHISPER_SRC="bin/whisper.cpp/build/bin/whisper-cli"
if [ ! -f "$WHISPER_SRC" ]; then
    echo "ERROR: whisper-cli binary not found at $WHISPER_SRC. Please compile it first."
    exit 1
fi
cp "$WHISPER_SRC" "$BUILD_DIR/usr/share/vozes/bin/whisper-cli"
# Create a symlink in /usr/bin for convenience
mkdir -p "$BUILD_DIR/usr/bin"
ln -s /usr/share/vozes/bin/whisper-cli "$BUILD_DIR/usr/bin/whisper-cli"

# 4. Copy Source Code, Data and Icon
cp -r src/* "$BUILD_DIR/usr/share/vozes/src/"
cp requirements.txt "$BUILD_DIR/usr/share/vozes/"
cp data/99-vozes.rules "$BUILD_DIR/etc/udev/rules.d/"
if [ -f "vozes.png" ]; then
    cp vozes.png "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/vozes.png"
    cp vozes.png "$BUILD_DIR/usr/share/vozes/data/vozes.png"
fi

# 5. Create Desktop Entry
cat <<EOF > "$BUILD_DIR/usr/share/applications/org.vozes.Vozes.desktop"
[Desktop Entry]
Name=Vozes
Comment=Dictado por voz profesional con Whisper.cpp
Exec=/usr/bin/vozes
Icon=vozes
Terminal=false
Type=Application
Categories=Utility;Audio;
Keywords=voice;speech;dictation;whisper;
EOF

# 6. Create Wrapper Script
cat <<EOF > "$BUILD_DIR/usr/bin/vozes"
#!/bin/bash
# Run from the installation directory
export PYTHONPATH=/usr/share/vozes:/usr/share/vozes/src:\$PYTHONPATH
# Path to the shared virtual environment created during postinst
if [ -f "/usr/share/vozes/venv/bin/activate" ]; then
    source /usr/share/vozes/venv/bin/activate
fi
exec python3 /usr/share/vozes/src/main.py "\$@"
EOF
chmod +x "$BUILD_DIR/usr/bin/vozes"

# 7. Control file (Metadata)
# We include python3-venv so we can create the local venv during install
cat <<EOF > "$BUILD_DIR/DEBIAN/control"
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Inled Group <hi@inled.es>
Depends: python3, python3-gi, python3-venv, python3-pip, libgirepository1.0-dev, libcairo2-dev, libportaudio2, libevdev2, libasound2, libpulse0
Description: Professional voice dictation system for Linux using native whisper.cpp.
 Includes hotkey support, wake-word (Hey Jarvis), and automatic typing.
EOF

# 8. Post-installation script (venv creation and udev)
cat <<EOF > "$BUILD_DIR/DEBIAN/postinst"
#!/bin/bash
set -e

echo "Setting up Vozes environment..."

# 1. Create Virtual Environment in /usr/share/vozes
# We do this to avoid polluting system python and ensure all deps work
cd /usr/share/vozes
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install --upgrade pip
# Install requirements (numpy >= 2.1.0 for Python 3.13)
pip install -r requirements.txt
# Special handling for openwakeword on Python 3.13 / ARM64
pip install openwakeword==0.6.0 --no-deps
# Pre-download models as root so they are available for all users
echo "Downloading wake word models..."
python3 -c "from openwakeword.utils import download_models; download_models()"

# 2. Reload udev rules
echo "Reloading udev rules..."
udevadm control --reload-rules || true
udevadm trigger || true

# 3. Ensure 'input' group
getent group input >/dev/null || groupadd -r input

echo "----------------------------------------------------------"
echo "Vozes installed successfully!"
echo "Run it from your application menu or type 'vozes' in terminal."
echo "----------------------------------------------------------"
EOF
chmod +x "$BUILD_DIR/DEBIAN/postinst"

# 9. Pre-removal script (clean venv)
cat <<EOF > "$BUILD_DIR/DEBIAN/prerm"
#!/bin/bash
set -e
if [ -d "/usr/share/vozes/venv" ]; then
    rm -rf /usr/share/vozes/venv
fi
EOF
chmod +x "$BUILD_DIR/DEBIAN/prerm"

# 10. Build the package
dpkg-deb --build "$BUILD_DIR"

echo "----------------------------------------------------------"
echo "Build complete: ${DEB_NAME}.deb"
echo "Install with: sudo apt install ./${DEB_NAME}.deb"
echo "----------------------------------------------------------"
