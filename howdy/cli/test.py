#!/usr/bin/env python3
# ==============================================================================
# HOWDY REAL-TIME BIOMETRIC RECOGNITION TEST & AR HUD
# Features:
#   1. Augmented Reality Biometric HUD overlay with dynamic corner brackets
#   2. Real-time Euclidean Distance matching against enrolled 128D vectors
#   3. Dynamic Camera Discovery (Auto-detects active USB or internal camera)
#   4. Live FPS, latency (ms), certainty threshold, and active model telemetry
#   5. Sanitized multi-user & distro-agnostic path resolution
# ==============================================================================

import os
import sys
import time
import json
import argparse
import getpass
import builtins
import numpy as np

os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["GST_DEBUG"] = "0"

try:
    import cv2
    import dlib
except ImportError as e:
    print(f"Error: Missing required computer vision libraries: {e}")
    sys.exit(1)

# Dynamically resolve Howdy installation directory
HOWDY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOWDY_DIR)

from recorders.video_capture import VideoCapture
import configparser

DATA_DIR = os.path.join(HOWDY_DIR, "dlib-data")
MODELS_DIR = os.path.join(HOWDY_DIR, "models")

# Resolve target user account
parser = argparse.ArgumentParser(description="Howdy Real-Time Biometric Test HUD", add_help=False)
parser.add_argument("-U", "--user", default=None, help="Target user account to test against")
args, _ = parser.parse_known_args()

target_user = args.user or getattr(builtins, "howdy_user", None) or os.environ.get("SUDO_USER")
if not target_user or target_user == "root":
    target_user = os.environ.get("USER") or getpass.getuser()

if not target_user:
    target_user = "default"

config = configparser.ConfigParser()
config_file = os.path.join(HOWDY_DIR, "config.ini")
if os.path.exists(config_file):
    config.read(config_file)
else:
    config["video"] = {"certainty": "4.0", "device_path": "/dev/video0"}

certainty_threshold = config.getfloat("video", "certainty", fallback=4.0)

# Load enrolled models for target user
model_path = os.path.join(MODELS_DIR, f"{target_user}.dat")
enrolled_vectors = []
enrolled_metadata = []

if os.path.exists(model_path):
    try:
        with open(model_path, "r") as f:
            raw_models = json.load(f)
            for m in raw_models:
                data = m.get("data", [])
                if data and len(data) > 0:
                    vec = data[0] if isinstance(data[0], list) else data
                    if len(vec) == 128:
                        enrolled_vectors.append(vec)
                        enrolled_metadata.append({"id": m.get("id", 0), "label": m.get("label", "enrolled")})
    except Exception as e:
        print(f"Notice: Error reading face models: {e}")

known_matrix = np.array(enrolled_vectors) if enrolled_vectors else None

shape_model = os.path.join(DATA_DIR, "shape_predictor_5_face_landmarks.dat")
face_model = os.path.join(DATA_DIR, "dlib_face_recognition_resnet_model_v1.dat")

if not os.path.isfile(shape_model) or not os.path.isfile(face_model):
    print(f"Error: Missing dlib models in {DATA_DIR}. Run: sudo /lib/security/howdy/dlib-data/install.sh")
    sys.exit(1)

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(shape_model)
encoder = dlib.face_recognition_model_v1(face_model)

try:
    cam = VideoCapture(config)
    cap = cam.internal
    device_path = cam.device_path
except Exception as e:
    print(f"Error: Could not initialize camera: {e}")
    sys.exit(1)

print(f"\n==================================================================")
print(f"        HOWDY REAL-TIME BIOMETRIC RECOGNITION TEST HUD            ")
print(f"==================================================================")
print(f"• Active Target User:      {target_user}")
print(f"• Enrolled Identity Scans: {len(enrolled_vectors)} models")
print(f"• Recognition Threshold:   {certainty_threshold} (Lower = Stricter)")
print(f"• Camera Device:           {device_path} [V4L2 Direct]")
print(f"==================================================================")
print("Opening camera test window. Press 'q' or ESC to exit.\n")

window_name = f"Howdy Face ID Biometric HUD [{target_user}]"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, 800, 600)

frame_count = 0
fps_timer = time.time()
fps = 0
rec_ms = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.02)
            continue

        frame_count += 1
        if time.time() - fps_timer >= 1.0:
            fps = frame_count
            frame_count = 0
            fps_timer = time.time()

        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces
        t0 = time.time()
        faces = detector(rgb_frame, 0)
        rec_ms = int((time.time() - t0) * 1000)

        for rect in faces:
            x1, y1, x2, y2 = rect.left(), rect.top(), rect.right(), rect.bottom()

            # Extract 128D embedding
            shape = predictor(rgb_frame, rect)
            face_desc = np.array(encoder.compute_face_descriptor(rgb_frame, shape, num_jitters=1))

            is_match = False
            best_dist = 99.0
            best_label = "unknown"
            best_id = -1

            if known_matrix is not None and len(known_matrix) > 0:
                distances = np.linalg.norm(known_matrix - face_desc, axis=1) * 10.0
                min_idx = np.argmin(distances)
                best_dist = distances[min_idx]
                if best_dist <= certainty_threshold:
                    is_match = True
                    best_id = enrolled_metadata[min_idx]["id"]
                    best_label = enrolled_metadata[min_idx]["label"]

            # Visual HUD overlay
            if is_match:
                hud_color = (0, 255, 64) # Neon Green
                title_text = f"MATCH: {target_user.upper()} [AUTHENTICATED]"
                sub_text = f"Certainty: {best_dist:.2f} (Model #{best_id}: {best_label})"
            else:
                hud_color = (48, 48, 255) # Bright Red
                title_text = "UNKNOWN FACE [ACCESS DENIED]"
                sub_text = f"Distance: {best_dist:.2f} (Threshold: {certainty_threshold})"

            # Corner brackets around face
            line_len = int((x2 - x1) * 0.25)
            thick = 2
            # Top-Left
            cv2.line(frame, (x1, y1), (x1 + line_len, y1), hud_color, thick)
            cv2.line(frame, (x1, y1), (x1, y1 + line_len), hud_color, thick)
            # Top-Right
            cv2.line(frame, (x2, y1), (x2 - line_len, y1), hud_color, thick)
            cv2.line(frame, (x2, y1), (x2, y1 + line_len), hud_color, thick)
            # Bottom-Left
            cv2.line(frame, (x1, y2), (x1 + line_len, y2), hud_color, thick)
            cv2.line(frame, (x1, y2), (x1, y2 - line_len), hud_color, thick)
            # Bottom-Right
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), hud_color, thick)
            cv2.line(frame, (x2, y2), (x2, y2 + line_len), hud_color, thick)

            # Badges
            cv2.rectangle(frame, (x1, max(0, y1 - 25)), (x1 + len(title_text) * 10, y1), hud_color, cv2.FILLED)
            cv2.putText(frame, title_text, (x1 + 4, max(12, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
            cv2.putText(frame, sub_text, (x1, min(h - 10, y2 + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, hud_color, 1, cv2.LINE_AA)

        # Global HUD status bar
        hud_bg = (10, 10, 10)
        cv2.rectangle(frame, (0, h - 35), (w, h), hud_bg, cv2.FILLED)
        info_str = f"NODE: {device_path} | RES: {w}x{h} | FPS: {fps} | LATENCY: {rec_ms}ms | MODELS: {len(enrolled_vectors)} | CERTAINTY: {certainty_threshold}"
        cv2.putText(frame, info_str, (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)

        cv2.imshow(window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break

finally:
    try:
        cam.release()
    except Exception:
        cap.release()
    cv2.destroyAllWindows()
    print("[Howdy Test] Diagnostic session closed.")
