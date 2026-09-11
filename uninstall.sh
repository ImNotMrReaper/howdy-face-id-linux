#!/usr/bin/env bash
# ==============================================================================
# Uninstaller for Howdy Linux Face ID Engine
# ==============================================================================

set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root (sudo ./uninstall.sh)"
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

echo "Howdy Face ID Engine has been completely uninstalled and PAM restored."
