#!/usr/bin/env bash
# ==============================================================================
# Universal 1-Click Uninstaller for Howdy Linux Face ID Engine
# Remote One-Liner:
#   curl -fsSL https://raw.githubusercontent.com/ImNotMrReaper/howdy-face-id-linux/main/uninstall.sh | sudo bash
# ==============================================================================

set -e

if [ "$(id -u)" -ne 0 ]; then
    echo -e "\033[1;31mError: This script must be run as root (sudo ./uninstall.sh)\033[0m"
    exit 1
fi

echo ">>> Restoring PAM configurations..."
for pam_file in /etc/pam.d/sudo /etc/pam.d/polkit-1 /etc/pam.d/common-auth; do
    if [ -f "${pam_file}.bak-howdy-auth" ]; then
        echo "    Restoring ${pam_file} from backup..."
        mv "${pam_file}.bak-howdy-auth" "${pam_file}"
    else
        if [ -f "${pam_file}" ]; then
            sed -i '/howdy\/pam\.py/d' "${pam_file}"
        fi
    fi
done

echo ">>> Removing CLI launchers..."
rm -f /usr/local/bin/howdy /usr/local/bin/howdy-scan /usr/local/bin/howdy-test

echo ">>> Removing Howdy library directory..."
rm -rf /lib/security/howdy
if [ -L "/usr/lib/security/howdy" ]; then
    rm -f /usr/lib/security/howdy
fi

echo -e "\n\033[1;32m✓ Howdy Face ID Engine has been completely uninstalled and PAM restored.\033[0m"
