#!/bin/bash
set -e

APP_NAME="vozes"
VERSION="1.0.0"
ARCH="amd64"
DEB_NAME="${APP_NAME}_${VERSION}_${ARCH}"

echo "Building Debian package $DEB_NAME..."

# Create directory structure
mkdir -p "$DEB_NAME/DEBIAN"
mkdir -p "$DEB_NAME/usr/bin"
mkdir -p "$DEB_NAME/usr/share/vozes"
mkdir -p "$DEB_NAME/usr/share/applications"
mkdir -p "$DEB_NAME/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$DEB_NAME/etc/udev/rules.d"

# Control file
cat <<EOF > "$DEB_NAME/DEBIAN/control"
Package: $APP_NAME
Version: $VERSION
Architecture: $ARCH
Maintainer: Vozes Dev <dev@vozes.org>
Depends: python3, python3-gi, python3-pip, python3-pyaudio, python3-evdev, python3-numpy, python3-dev, portaudio19-dev, libevdev-dev, cmake, pkg-config, g++, git, make, build-essential
Description: A professional voice dictation system for Linux using native whisper.cpp.
EOF

# Postinst script to reload udev rules
cat <<EOF > "$DEB_NAME/DEBIAN/postinst"
#!/bin/bash
set -e
# Apply udev rules
udevadm control --reload-rules || true
udevadm trigger || true
# Ensure input group exists
getent group input >/dev/null || groupadd -r input
EOF
chmod +x "$DEB_NAME/DEBIAN/postinst"

# Copy files
cp -r src "$DEB_NAME/usr/share/vozes/"
cp requirements.txt "$DEB_NAME/usr/share/vozes/"
cp data/99-vozes.rules "$DEB_NAME/etc/udev/rules.d/"
# Assuming a generic icon or empty for now if not created
touch "$DEB_NAME/usr/share/icons/hicolor/scalable/apps/vozes.svg"

# Desktop file
cat <<EOF > "$DEB_NAME/usr/share/applications/org.vozes.Vozes.desktop"
[Desktop Entry]
Name=Vozes
Comment=Voice Dictation with Whisper
Exec=/usr/bin/vozes
Icon=vozes
Terminal=false
Type=Application
Categories=Utility;Audio;
EOF

# Wrapper script
cat <<EOF > "$DEB_NAME/usr/bin/vozes"
#!/bin/bash
cd /usr/share/vozes
# Ensure deps are installed via pip in user space or rely on system packages
export PYTHONPATH=/usr/share/vozes/src
exec python3 /usr/share/vozes/src/main.py "\$@"
EOF
chmod +x "$DEB_NAME/usr/bin/vozes"

# Build package
dpkg-deb --build "$DEB_NAME"
echo "Built $DEB_NAME.deb successfully."
