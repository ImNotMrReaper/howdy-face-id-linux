# Howdy Linux Face ID Biometric Engine 🛡️👁️

Universal, production-ready facial recognition authentication system and multi-camera biometric engine for Linux.

Works seamlessly on **Ubuntu Desktop, Ubuntu Server, Debian, Linux Mint, Pop!_OS, Fedora, and Arch Linux**.

---

## ⚡ Key Architectural Enhancements

Standard upstream Howdy faces several practical challenges on modern Linux distributions (especially on Ubuntu 24.04, Python 3.12 PEP 668, and desktop docks). This distribution integrates critical enhancements:

1. **Dynamic External USB Camera & IR Discovery (`recorders/video_capture.py`):**
   - Automatically scans `/dev/v4l/by-id/` prioritizing external high-definition USB webcams when docked at a desk, seamlessly falling back to integrated laptop IR/RGB webcams (`/dev/video0`).
   - Direct `cv2.CAP_V4L2` streaming with OpenCV/GStreamer warning suppression for silent, clean execution.

2. **Closed-Lid Docked Desk Authentication (`pam.py`):**
   - Standard setups abort if the laptop lid is closed. This engine checks if an external USB camera is present; if detected, face authentication proceeds normally even with the laptop closed and docked.

3. **1.0-Second Mechanical Shutter Auto-Fallback (`compare.py`):**
   - Laptops with mechanical privacy sliders (e.g. Dell, Lenovo ThinkPad) or dark environments often leave users waiting 7–10 seconds for a timeout.
   - This engine detects covered shutters or unlit frames in $\ge$ 1.0 second, emits an informative message (`Camera covered or unlit, falling back...`), and immediately hands authentication over to your fingerprint reader or password prompt.

4. **Multi-Angle 5-Pose Face ID Calibration (`howdy-scan` / `howdy scan`):**
   - Replaces single-snapshot enrollment with a 5-angle biometric calibration sequence (Center Neutral, Left 15°, Right 15°, Tilt Up, Tilt Down).
   - **Real-time Laplacian Blur Filter:** Discards motion-blurred frames.
   - **CLAHE Adaptive Histogram Equalization:** Normalizes harsh shadows and dim room lighting.
   - **5x Neural Vector Jittering:** Generates high-accuracy 128D dlib ResNet biometric embeddings.

5. **Real-Time Augmented Reality Diagnostic HUD (`howdy-test` / `howdy test`):**
   - Visual test window with AR corner brackets tracking detected faces.
   - Displays live Euclidean distance vs. certainty threshold, identity match badges (`[✓ MATCH]`), frame resolution, FPS, and millisecond latency.

6. **Zero-Lockout PAM Integration:**
   - Structured as `Face -> Fingerprint -> Password` across `sudo`, `polkit-1`, and login/lockscreen.
   - Always preserves standard Unix password fallback (`pam_unix.so try_first_pass`).

---

## 🚀 Quick Start & Installation

### Option 1: Install via Debian Package (`.deb`)
*Ideal for Ubuntu Desktop, Ubuntu Server, Debian, Linux Mint, and Pop!_OS.*

```bash
# 1. Download and install the debian package
sudo dpkg -i howdy-face-id-auth_1.0.0_amd64.deb

# 2. Resolve system dependencies automatically
sudo apt-get install -f
```

### Option 2: Universal Source Installer (`install.sh`)
*Works on any Linux distribution (Ubuntu, Debian, Fedora, Arch, RHEL).*

```bash
git clone https://github.com/ImNotMrReaper/howdy-face-id-linux.git
cd howdy-face-id-linux
sudo ./install.sh
```

---

## 🎮 Enrolling Your Face & Testing

### 1. Run 5-Angle Face ID Calibration
Calibrate your face profile across 5 distinct poses:
```bash
sudo howdy scan
# Or directly:
sudo howdy-scan
```
*To enroll for a specific user:*
```bash
sudo howdy scan --user <username>
```

### 2. Launch the Augmented Reality Diagnostic HUD
Verify your camera alignment, certainty scores, and real-time biometric matching:
```bash
sudo howdy test
# Or directly:
sudo howdy-test
```
*Press `q` or `ESC` to exit the HUD.*

### 3. List & Manage Enrolled Models
```bash
# List enrolled biometric models:
sudo howdy list

# Remove a specific model ID:
sudo howdy remove <ID>

# Clear all models for a user:
sudo howdy clear
```

---

## 🔐 PAM System Authentication (`sudo`, Login, Lockscreen)

The installer automatically configures your PAM pipeline across:
- **Terminal Sudo:** `/etc/pam.d/sudo`
- **Desktop Privilege Elevation:** `/etc/pam.d/polkit-1`
- **Central Common Auth:** `/etc/pam.d/common-auth`
- **Lockscreen & Login:** `/etc/pam.d/gdm-password` (or lightdm/sddm)

```pam
# Recommended Authentication Flow:
auth       sufficient   pam_python.so /lib/security/howdy/pam.py
auth       sufficient   pam_python.so /lib/security/dp_fprint_pam.py
auth       sufficient   pam_unix.so try_first_pass nullok
```

**Zero-Lockout Guarantee:** If your camera is covered, unplugged, or your face is not recognized, authentication immediately cascades to fingerprint or standard password. You can never be locked out.

---

## 🛠️ Building the Debian Package from Source

To compile and build a fresh `.deb` binary on any Debian/Ubuntu machine:

```bash
./build_deb.sh
```
The resulting package will be generated at `./howdy-face-id-auth_1.0.0_amd64.deb`.

---

## 🗑️ Uninstallation

To completely remove the package and restore stock PAM configurations:

```bash
# Via script:
sudo ./uninstall.sh

# Or via apt:
sudo apt remove howdy-face-id-auth
```

---

## 📋 Distribution Compatibility Matrix

| Distribution | Status | Installation Method |
|---|:---:|---|
| **Ubuntu 24.04 LTS (Desktop & Server)** | ✅ Fully Verified | `.deb` or `install.sh` |
| **Ubuntu 22.04 LTS (Desktop & Server)** | ✅ Fully Verified | `.deb` or `install.sh` |
| **Debian 12 (Bookworm)** | ✅ Supported | `.deb` or `install.sh` |
| **Linux Mint 21 / 22** | ✅ Supported | `.deb` or `install.sh` |
| **Pop!_OS 22.04 / 24.04** | ✅ Supported | `.deb` or `install.sh` |
| **Fedora 38 / 39 / 40** | ✅ Supported | `install.sh` |
| **Arch Linux** | ✅ Supported | `install.sh` |

---

## 📄 License
MIT License. Open-source and free for personal and enterprise use.
