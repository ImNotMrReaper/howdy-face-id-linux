#!/usr/bin/env bash
# ==============================================================================
# Universal Multi-Distribution 1-Line Installer for Howdy Linux Face ID Engine
# Supports: Ubuntu, Debian, Fedora, Arch Linux, openSUSE, Linux Mint, Pop!_OS
# One-Line Remote Execution:
#   curl -fsSL https://raw.githubusercontent.com/ImNotMrReaper/howdy-face-id-linux/main/install.sh | sudo bash
# ==============================================================================

set -e

if [ "$(id -u)" -ne 0 ]; then
    echo -e "\033[1;31mError: This script must be run as root (sudo ./install.sh)\033[0m"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"

# Auto-clone repository if executed directly from curl/pipe
if [ ! -d "${SCRIPT_DIR}/howdy" ]; then
    echo ">>> Running from remote pipe. Cloning latest repository..."
    TMP_CLONE="$(mktemp -d /tmp/howdy-install.XXXXXX)"
    if ! command -v git >/dev/null 2>&1; then
        if command -v apt-get >/dev/null 2>&1; then apt-get update -qq && apt-get install -y -qq git;
        elif command -v dnf >/dev/null 2>&1; then dnf install -y git;
        elif command -v pacman >/dev/null 2>&1; then pacman -Sy --needed --noconfirm git;
        elif command -v zypper >/dev/null 2>&1; then zypper --non-interactive install git; fi
    fi
    git clone --depth 1 https://github.com/ImNotMrReaper/howdy-face-id-linux.git "${TMP_CLONE}"
    SCRIPT_DIR="${TMP_CLONE}"
    trap "rm -rf '${TMP_CLONE}'" EXIT
fi

TARGET_LIB_DIR="/lib/security/howdy"
TARGET_BIN_DIR="/usr/local/bin"

echo -e "\033[1;35m=======================================================\033[0m"
echo -e "\033[1;35m 🛡️  HOWDY FACE ID BIOMETRIC ENGINE INSTALLER          \033[0m"
echo -e "\033[1;35m=======================================================\033[0m\n"

# 1. Detect Package Manager & Install System Dependencies
echo -e ">>> \033[1;34m[1/6] Detecting Linux Distribution & Package Manager...\033[0m"

if command -v apt-get >/dev/null 2>&1; then
    echo "    Detected Debian/Ubuntu-based distribution."
    apt-get update -y
    apt-get install -y cmake build-essential libopenblas-dev liblapack-dev \
        python3-dev python3-numpy python3-opencv python3-pip python3-cryptography \
        bzip2 wget curl libpam-python || true
elif command -v dnf >/dev/null 2>&1; then
    echo "    Detected Fedora/RHEL-based distribution."
    dnf install -y cmake gcc-c++ make openblas-devel lapack-devel \
        python3-devel python3-numpy python3-opencv python3-pip python3-cryptography \
        bzip2 wget curl || true
elif command -v pacman >/dev/null 2>&1; then
    echo "    Detected Arch Linux-based distribution."
    pacman -Sy --needed --noconfirm cmake gcc make openblas lapack \
        python python-numpy python-opencv python-pip python-cryptography \
        bzip2 wget curl || true
elif command -v zypper >/dev/null 2>&1; then
    echo "    Detected openSUSE distribution."
    zypper --non-interactive install cmake gcc-c++ make openblas-devel lapack-devel \
        python3-devel python3-numpy python3-opencv python3-pip python3-cryptography \
        bzip2 wget curl || true
else
    echo "    Warning: Unknown package manager. Please ensure cmake, opencv, and python3-dlib are installed."
fi

# 2. Check Python dlib & ONNX Runtime Modules
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

if python3 -c "import onnxruntime" >/dev/null 2>&1; then
    echo "    onnxruntime is already installed and functional."
else
    echo "    Installing onnxruntime via pip..."
    pip3 install onnxruntime --break-system-packages || pip3 install onnxruntime || {
        echo -e "\033[1;33mWarning: Failed to install onnxruntime via pip. Checking fallback...\033[0m"
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

# 4. Download Neural Network Weights & Deep ONNX Models
echo -e ">>> \033[1;34m[4/6] Checking dlib ResNet, YuNet CNN & MiniFASNet models...\033[0m"
DATA_DIR="${TARGET_LIB_DIR}/dlib-data"
if [ ! -f "${DATA_DIR}/shape_predictor_5_face_landmarks.dat" ] || [ ! -f "${DATA_DIR}/dlib_face_recognition_resnet_model_v1.dat" ]; then
    echo "    Downloading required dlib neural network weights..."
    cd "${DATA_DIR}"
    bash install.sh
    cd "${SCRIPT_DIR}"
else
    echo "    dlib neural network models already present."
fi

MODELS_DIR="${TARGET_LIB_DIR}/models"
if [ ! -f "${MODELS_DIR}/face_detection_yunet_2023mar.onnx" ]; then
    echo "    Downloading YuNet CNN face detection model..."
    curl -fsSL "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" -o "${MODELS_DIR}/face_detection_yunet_2023mar.onnx" || true
else
    echo "    YuNet CNN model already present."
fi

if [ ! -f "${MODELS_DIR}/minifasnet_v2.onnx" ]; then
    echo "    Downloading MiniFASNet passive anti-spoofing model..."
    curl -fsSL "https://huggingface.co/garciafido/minifasnet-v2-anti-spoofing-onnx/resolve/main/minifasnet_v2.onnx" -o "${MODELS_DIR}/minifasnet_v2.onnx" || true
else
    echo "    MiniFASNet anti-spoofing model already present."
fi

# 5. Install CLI Executables
echo -e ">>> \033[1;34m[5/6] Installing CLI executables to ${TARGET_BIN_DIR}...\033[0m"
mkdir -p "${TARGET_BIN_DIR}"
cp "${SCRIPT_DIR}/bin/howdy" "${TARGET_BIN_DIR}/howdy"
cp "${SCRIPT_DIR}/bin/howdy-scan" "${TARGET_BIN_DIR}/howdy-scan"
cp "${SCRIPT_DIR}/bin/howdy-test" "${TARGET_BIN_DIR}/howdy-test"
cp "${SCRIPT_DIR}/bin/howdy-hud-enroll" "${TARGET_BIN_DIR}/howdy-hud-enroll"
chmod 755 "${TARGET_BIN_DIR}/howdy" "${TARGET_BIN_DIR}/howdy-scan" "${TARGET_BIN_DIR}/howdy-test" "${TARGET_BIN_DIR}/howdy-hud-enroll"

# 6. Configure PAM Pipeline (With Safe Backups & Zero-Lockout Guarantee)
echo -e ">>> \033[1;34m[6/6] Configuring PAM authentication stack...\033[0m"

configure_pam() {
    local pam_file="$1"
    if [ -f "${pam_file}" ]; then
        if ! grep -q "howdy/pam.py" "${pam_file}"; then
            echo "    Backing up ${pam_file} -> ${pam_file}.bak-howdy-auth"
            cp "${pam_file}" "${pam_file}.bak-howdy-auth"
            
            # Place Howdy before unix authentication or fingerprint modules
            if grep -q "reaper_fprint_pam\.py" "${pam_file}"; then
                sed -i '/reaper_fprint_pam\.py/i auth\tsufficient\tpam_python.so /lib/security/howdy/pam.py' "${pam_file}"
            elif grep -q "dp_fprint_pam\.py" "${pam_file}"; then
                sed -i '/dp_fprint_pam\.py/i auth\tsufficient\tpam_python.so /lib/security/howdy/pam.py' "${pam_file}"
            elif grep -q "pam_fprintd\.so" "${pam_file}"; then
                sed -i '/pam_fprintd\.so/i auth\tsufficient\tpam_python.so /lib/security/howdy/pam.py' "${pam_file}"
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
echo "  • Enroll Face (5-Angle Calibration): sudo howdy scan"
echo "  • Multi-Camera Diagnostic HUD:       sudo howdy test"
echo "  • Authenticate Commands:             sudo whoami"
echo ""

# Interactive enrollment prompt if attached to a terminal
if [ -t 0 ] || [ -r /dev/tty ]; then
    echo -ne "\033[1;33mWould you like to enroll your face right now (5-Angle Guided Calibration)? [Y/n]: \033[0m"
    read -r ENROLL_PROMPT < /dev/tty || ENROLL_PROMPT="y"
    if [[ "$ENROLL_PROMPT" =~ ^[Yy]?$ ]]; then
        TARGET_USER="${SUDO_USER:-$USER}"
        echo -e "\nStarting 5-angle biometric calibration for \033[1m${TARGET_USER}\033[0m...\n"
        howdy scan --user "${TARGET_USER}" || true
    fi
fi
