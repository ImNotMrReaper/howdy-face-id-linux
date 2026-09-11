#!/usr/bin/env bash
# ==============================================================================
# Universal Multi-Distribution Installer for Howdy Linux Face ID Engine
# Supports: Ubuntu, Debian, Fedora, Arch Linux, Linux Mint, Pop!_OS
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_LIB_DIR="/lib/security/howdy"
TARGET_BIN_DIR="/usr/local/bin"

if [ "$(id -u)" -ne 0 ]; then
    echo -e "\033[1;31mError: This script must be run as root (sudo ./install.sh)\033[0m"
    exit 1
fi

echo -e "\033[1;35m=======================================================\033[0m"
echo -e "\033[1;35m 🛡️  HOWDY FACE ID BIOMETRIC ENGINE INSTALLER          \033[0m"
echo -e "\033[1;35m=======================================================\033[0m\n"

# 1. Detect Package Manager & Install System Dependencies
echo -e ">>> \033[1;34m[1/6] Detecting Linux Distribution & Package Manager...\033[0m"

if command -v apt-get >/dev/null 2>&1; then
    echo "    Detected Debian/Ubuntu-based distribution."
    apt-get update -y
    apt-get install -y cmake build-essential libopenblas-dev liblapack-dev \
        python3-dev python3-numpy python3-opencv python3-pip \
        bzip2 wget curl libpam-python || true
elif command -v dnf >/dev/null 2>&1; then
    echo "    Detected Fedora/RHEL-based distribution."
    dnf install -y cmake gcc-c++ make openblas-devel lapack-devel \
        python3-devel python3-numpy python3-opencv python3-pip \
        bzip2 wget curl || true
elif command -v pacman >/dev/null 2>&1; then
    echo "    Detected Arch Linux-based distribution."
    pacman -Sy --needed --noconfirm cmake gcc make openblas lapack \
        python python-numpy python-opencv python-pip \
        bzip2 wget curl || true
else
    echo "    Warning: Unknown package manager. Please ensure cmake, opencv, and python3-dlib are installed."
fi

# 2. Check Python dlib Module
echo -e ">>> \033[1;34m[2/6] Verifying Python dlib & computer vision dependencies...\033[0m"
if python3 -c "import dlib" >/dev/null 2>&1; then
    echo "    dlib is already installed and functional."
else
    echo "    Installing dlib via pip..."
    pip3 install dlib --break-system-packages --no-cache-dir || pip3 install dlib || {
        echo -e "\033[1;31mError: Failed to install dlib. Please check build dependencies.\033[0m"
        exit 1
    }
fi

# 3. Deploy Engine Core Files
echo -e ">>> \033[1;34m[3/6] Deploying Howdy engine to ${TARGET_LIB_DIR}...\033[0m"
mkdir -p "${TARGET_LIB_DIR}"
mkdir -p "${TARGET_LIB_DIR}/cli"
mkdir -p "${TARGET_LIB_DIR}/recorders"
mkdir -p "${TARGET_LIB_DIR}/dlib-data"
mkdir -p "${TARGET_LIB_DIR}/models"
mkdir -p "${TARGET_LIB_DIR}/snapshots"

cp -r "${SCRIPT_DIR}/howdy/"* "${TARGET_LIB_DIR}/"
chmod 755 "${TARGET_LIB_DIR}"/*.py "${TARGET_LIB_DIR}/cli"/*.py "${TARGET_LIB_DIR}/recorders"/*.py 2>/dev/null || true
chmod 777 "${TARGET_LIB_DIR}/snapshots" 2>/dev/null || true

# Symlink for distros using /usr/lib/security
if [ ! -d "/usr/lib/security/howdy" ] && [ -d "/usr/lib/security" ]; then
    ln -sf "${TARGET_LIB_DIR}" "/usr/lib/security/howdy" 2>/dev/null || true
fi

# 4. Download Neural Network Weights
echo -e ">>> \033[1;34m[4/6] Checking dlib ResNet & facial landmark models...\033[0m"
DATA_DIR="${TARGET_LIB_DIR}/dlib-data"
if [ ! -f "${DATA_DIR}/shape_predictor_5_face_landmarks.dat" ] || [ ! -f "${DATA_DIR}/dlib_face_recognition_resnet_model_v1.dat" ]; then
    echo "    Downloading required neural network weights (this may take a minute)..."
    cd "${DATA_DIR}"
    bash install.sh
    cd "${SCRIPT_DIR}"
else
    echo "    Neural network models already present."
fi

# 5. Install CLI Executables
echo -e ">>> \033[1;34m[5/6] Installing CLI executables to ${TARGET_BIN_DIR}...\033[0m"
mkdir -p "${TARGET_BIN_DIR}"
cp "${SCRIPT_DIR}/bin/howdy" "${TARGET_BIN_DIR}/howdy"
cp "${SCRIPT_DIR}/bin/howdy-scan" "${TARGET_BIN_DIR}/howdy-scan"
cp "${SCRIPT_DIR}/bin/howdy-test" "${TARGET_BIN_DIR}/howdy-test"
chmod 755 "${TARGET_BIN_DIR}/howdy" "${TARGET_BIN_DIR}/howdy-scan" "${TARGET_BIN_DIR}/howdy-test"

# 6. Configure PAM Pipeline (With Safe Backups & Zero-Lockout Guarantee)
echo -e ">>> \033[1;34m[6/6] Configuring PAM authentication stack...\033[0m"

configure_pam() {
    local pam_file="$1"
    if [ -f "${pam_file}" ]; then
        if ! grep -q "howdy/pam.py" "${pam_file}"; then
            echo "    Backing up ${pam_file} -> ${pam_file}.bak-howdy-auth"
            cp "${pam_file}" "${pam_file}.bak-howdy-auth"
            
            # Place Howdy before unix authentication or fingerprint modules
            if grep -q "pam_fprintd\.so" "${pam_file}"; then
                sed -i '/pam_fprintd\.so/i auth\tsufficient\tpam_python.so /lib/security/howdy/pam.py' "${pam_file}"
            elif grep -q "dp_fprint_pam\.py" "${pam_file}"; then
                sed -i '/dp_fprint_pam\.py/i auth\tsufficient\tpam_python.so /lib/security/howdy/pam.py' "${pam_file}"
            elif grep -q "reaper_fprint_pam\.py" "${pam_file}"; then
                sed -i '/reaper_fprint_pam\.py/i auth\tsufficient\tpam_python.so /lib/security/howdy/pam.py' "${pam_file}"
            elif grep -q "pam_unix\.so" "${pam_file}"; then
                sed -i '/pam_unix\.so/i auth\tsufficient\tpam_python.so /lib/security/howdy/pam.py' "${pam_file}"
            else
                echo "auth sufficient pam_python.so /lib/security/howdy/pam.py" >> "${pam_file}"
            fi
            echo "    Configured Howdy in ${pam_file}"
        else
            echo "    ${pam_file} already configured with Howdy."
        fi
    fi
}

configure_pam "/etc/pam.d/sudo"
configure_pam "/etc/pam.d/polkit-1"
configure_pam "/etc/pam.d/common-auth"

echo -e "\n\033[1;32m=======================================================\033[0m"
echo -e "\033[1;32m 🎉 HOWDY FACE ID ENGINE SUCCESSFULLY INSTALLED!       \033[0m"
echo -e "\033[1;32m=======================================================\033[0m\n"
echo "Quick Start Instructions:"
echo "  1. Enroll your face (5-Angle Calibration):"
echo -e "     \033[1;36msudo howdy scan\033[0m   (or \033[1;36msudo howdy-scan\033[0m)"
echo ""
echo "  2. Test real-time recognition HUD:"
echo -e "     \033[1;36msudo howdy test\033[0m   (or \033[1;36msudo howdy-test\033[0m)"
echo ""
echo "  3. Authenticate commands:"
echo -e "     \033[1;36msudo whoami\033[0m"
echo ""
