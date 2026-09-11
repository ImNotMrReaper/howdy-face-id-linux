#!/usr/bin/env bash
# ==============================================================================
# Builds howdy-face-id-auth_1.0.0_amd64.deb for Ubuntu & Debian
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build/deb"
VERSION="1.0.0"
PKG_NAME="howdy-face-id-auth"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo "amd64")"
DEB_FILE="${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo ">>> Building ${DEB_FILE}..."

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/local/bin"
mkdir -p "${BUILD_DIR}/lib/security/howdy"
mkdir -p "${BUILD_DIR}/lib/security/howdy/cli"
mkdir -p "${BUILD_DIR}/lib/security/howdy/recorders"
mkdir -p "${BUILD_DIR}/lib/security/howdy/dlib-data"
mkdir -p "${BUILD_DIR}/lib/security/howdy/models"
mkdir -p "${BUILD_DIR}/lib/security/howdy/snapshots"

# 1. Copy CLI executables
cp "${SCRIPT_DIR}/bin/howdy" "${BUILD_DIR}/usr/local/bin/howdy"
cp "${SCRIPT_DIR}/bin/howdy-scan" "${BUILD_DIR}/usr/local/bin/howdy-scan"
cp "${SCRIPT_DIR}/bin/howdy-test" "${BUILD_DIR}/usr/local/bin/howdy-test"
chmod 755 "${BUILD_DIR}/usr/local/bin/"*

# 2. Copy Howdy Core Files
cp -r "${SCRIPT_DIR}/howdy/"* "${BUILD_DIR}/lib/security/howdy/"
chmod 755 "${BUILD_DIR}/lib/security/howdy"/*.py 2>/dev/null || true
chmod 755 "${BUILD_DIR}/lib/security/howdy/cli"/*.py 2>/dev/null || true
chmod 755 "${BUILD_DIR}/lib/security/howdy/recorders"/*.py 2>/dev/null || true
chmod 777 "${BUILD_DIR}/lib/security/howdy/snapshots" 2>/dev/null || true

# Remove any personal models or test files that might have slipped in
rm -f "${BUILD_DIR}/lib/security/howdy/models/"*.dat
rm -f "${BUILD_DIR}/lib/security/howdy/snapshots/"*.jpg
touch "${BUILD_DIR}/lib/security/howdy/models/.gitkeep"
touch "${BUILD_DIR}/lib/security/howdy/snapshots/.gitkeep"

# 3. Control file
cat << EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${VERSION}
Section: admin
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-numpy, python3-opencv, python3-pip, bzip2, wget, curl
Maintainer: Linux Biometrics Team <admin@localhost>
Description: Enterprise Linux Face ID Biometric Authentication Engine
 Complete facial recognition authentication system for Linux based on Howdy.
 Includes dynamic external USB camera discovery, laptop closed-lid docking support,
 rapid mechanical camera shutter fallback, 5-angle guided Face ID calibration,
 and real-time augmented reality diagnostic HUD.
EOF

# 4. Post-install script
cat << 'EOFPOST' > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e

chmod 777 /lib/security/howdy/snapshots 2>/dev/null || true

if [ ! -d "/usr/lib/security/howdy" ] && [ -d "/usr/lib/security" ]; then
    ln -sf /lib/security/howdy /usr/lib/security/howdy 2>/dev/null || true
fi

DATA_DIR="/lib/security/howdy/dlib-data"
if [ -d "$DATA_DIR" ]; then
    if [ ! -f "${DATA_DIR}/shape_predictor_5_face_landmarks.dat" ] || [ ! -f "${DATA_DIR}/dlib_face_recognition_resnet_model_v1.dat" ]; then
        echo ">>> Downloading dlib neural network models..."
        cd "$DATA_DIR"
        bash install.sh 2>/dev/null || true
    fi
fi

configure_pam() {
    file="$1"
    if [ -f "$file" ] && ! grep -q "howdy/pam.py" "$file"; then
        cp "$file" "${file}.bak-howdy-auth"
        if grep -q "pam_fprintd\.so" "$file"; then
            sed -i '/pam_fprintd\.so/i auth	sufficient	pam_python.so /lib/security/howdy/pam.py' "$file"
        elif grep -q "dp_fprint_pam\.py" "$file"; then
            sed -i '/dp_fprint_pam\.py/i auth	sufficient	pam_python.so /lib/security/howdy/pam.py' "$file"
        elif grep -q "reaper_fprint_pam\.py" "$file"; then
            sed -i '/reaper_fprint_pam\.py/i auth	sufficient	pam_python.so /lib/security/howdy/pam.py' "$file"
        elif grep -q "pam_unix\.so" "$file"; then
            sed -i '/pam_unix\.so/i auth	sufficient	pam_python.so /lib/security/howdy/pam.py' "$file"
        fi
    fi
}

configure_pam "/etc/pam.d/sudo"
configure_pam "/etc/pam.d/polkit-1"
configure_pam "/etc/pam.d/common-auth"

echo "Howdy Face ID Biometric Engine installed successfully!"
echo "Run 'sudo howdy scan' to enroll your face."
exit 0
EOFPOST
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

# 5. Pre-remove script
cat << 'EOFPRERM' > "${BUILD_DIR}/DEBIAN/prerm"
#!/bin/sh
set -e

for file in /etc/pam.d/sudo /etc/pam.d/polkit-1 /etc/pam.d/common-auth; do
    if [ -f "${file}.bak-howdy-auth" ]; then
        mv "${file}.bak-howdy-auth" "$file"
    else
        sed -i '/howdy\/pam\.py/d' "$file" 2>/dev/null || true
    fi
done

rm -f /usr/local/bin/howdy
rm -f /usr/local/bin/howdy-scan
rm -f /usr/local/bin/howdy-test

if [ -L "/usr/lib/security/howdy" ]; then
    rm -f /usr/lib/security/howdy
fi

exit 0
EOFPRERM
chmod 755 "${BUILD_DIR}/DEBIAN/prerm"

# 6. Build debian package
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "${SCRIPT_DIR}/${DEB_FILE}"

echo ""
echo "🎉 Package created: ${SCRIPT_DIR}/${DEB_FILE}"
echo "   Install on any Debian/Ubuntu system with:"
echo "   sudo dpkg -i ${DEB_FILE}"
