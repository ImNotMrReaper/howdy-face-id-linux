import os
import sys
import time
import json
import glob
import re
import configparser
import dlib
import cv2
import numpy as np
import concurrent.futures

# Setup paths and config
howdy_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, howdy_dir)
from recorders.video_capture import discover_capture_devices, open_single_camera, format_camera_name
import security

config = configparser.ConfigParser()
config.read(os.path.join(howdy_dir, "config.ini"))
certainty_threshold = config.getfloat("video", "certainty", fallback=3.5)
user = os.getenv("SUDO_USER") or os.getenv("USER") or "mr-reaper"

# Load models via hardware-bound AES-256-GCM security module
enrolled_vectors = []
enrolled_metadata = []
try:
    models = security.load_user_models(user)
    for m in models:
        for vec in m.get("data", []):
            if len(vec) == 128:
                enrolled_vectors.append(vec)
                enrolled_metadata.append({"id": m.get("id", 0), "label": m.get("label", "enrolled")})
except Exception as e:
    print(f"Notice loading face models: {e}")

known_matrix = np.array(enrolled_vectors) if enrolled_vectors else None

# Discover and open all initial candidate cameras
candidates = discover_capture_devices()
with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(candidates))) as executor:
    results = list(executor.map(lambda c: open_single_camera(c, fw=640, fh=480), candidates))
caps = [c for c in results if c is not None]

print("\n==================================================================")
print("        HOWDY UNIVERSAL MULTI-CAMERA BIOMETRIC HUD (PLUG & PLAY)  ")
print("==================================================================")
print(f"• Active Target User: {user}")
print(f"• Enrolled Identity Scans: {len(enrolled_vectors)} models (AES-256-GCM)")
print(f"• Recognition Threshold (Certainty): {certainty_threshold} (Lower = Stricter)")
print(f"• Armed Cameras ({len(caps)} active concurrently):")
for idx, c in enumerate(caps):
    print(f"    [{idx + 1}] {c['name']} ({c['path']})")
print("• Dynamic Hotplug: Active (automatically adds/removes cameras live)")
print("==================================================================")
print("Opening multi-angle camera test window. Press 'q' or ESC to exit.\n")

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(os.path.join(howdy_dir, "dlib-data", "shape_predictor_5_face_landmarks.dat"))
encoder = dlib.face_recognition_model_v1(os.path.join(howdy_dir, "dlib-data", "dlib_face_recognition_resnet_model_v1.dat"))

WIN_NAME = "Howdy Multi-Angle Face ID Biometric HUD"
cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)

TILE_W = 640
TILE_H = 480

def build_hud_grid(tiles, active_caps, cur_user, enc_count, cert_thresh):
    N = len(tiles)
    if N == 0:
        standby = np.zeros((480, 640, 3), dtype=np.uint8)
        standby[:] = (20, 20, 20)
        cv2.putText(standby, "HOWDY BIOMETRIC HUD", (170, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(standby, "NO CAMERAS CONNECTED", (160, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(standby, "Plug in a USB webcam or open laptop lid...", (140, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1, cv2.LINE_AA)
        cv2.putText(standby, "Press 'q' or ESC to exit", (230, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 120, 120), 1, cv2.LINE_AA)
        return standby, 640, 480

    norm_tiles = []
    for t in tiles:
        if t.shape[1] != TILE_W or t.shape[0] != TILE_H:
            norm_tiles.append(cv2.resize(t, (TILE_W, TILE_H), interpolation=cv2.INTER_AREA))
        else:
            norm_tiles.append(t)

    if N == 1:
        return norm_tiles[0], TILE_W, TILE_H

    if N == 2:
        return np.hstack([norm_tiles[0], norm_tiles[1]]), TILE_W * 2, TILE_H

    cols = 2 if N <= 4 else int(np.ceil(np.sqrt(N)))
    rows = int(np.ceil(N / cols))
    total_slots = cols * rows

    while len(norm_tiles) < total_slots:
        info_tile = np.zeros((TILE_H, TILE_W, 3), dtype=np.uint8)
        info_tile[:] = (18, 18, 18)
        cv2.rectangle(info_tile, (10, 10), (TILE_W - 10, TILE_H - 10), (50, 50, 50), 1)
        cv2.rectangle(info_tile, (10, 10), (TILE_W - 10, 45), (32, 32, 32), cv2.FILLED)
        cv2.putText(info_tile, "SYSTEM BIOMETRICS & TELEMETRY", (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1, cv2.LINE_AA)

        y = 80
        info_items = [
            f"User Target: {cur_user}",
            f"Enrolled Faces: {enc_count} models (AES-256-GCM)",
            f"Active Sensors: {len(active_caps)} cameras armed",
            f"Certainty Threshold: {cert_thresh}",
            "Encryption: Hardware-Bound (HKDF-SHA256)",
            "Hotplug Status: Monitoring /dev/video*",
            "Controls: Press 'q' to exit HUD"
        ]
        for item in info_items:
            cv2.putText(info_tile, f"• {item}", (25, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)
            y += 34

        y += 10
        cv2.putText(info_tile, "ARMED SENSORS:", (25, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 128), 1, cv2.LINE_AA)
        y += 24
        for c_idx, c in enumerate(active_caps, 1):
            cv2.putText(info_tile, f"  [{c_idx}] {c['name']}", (25, y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 220, 255), 1, cv2.LINE_AA)
            y += 22

        norm_tiles.append(info_tile)

    grid_rows = []
    for r in range(rows):
        grid_rows.append(np.hstack(norm_tiles[r * cols : (r + 1) * cols]))
    grid = np.vstack(grid_rows)
    return grid, TILE_W * cols, TILE_H * rows

last_win_dims = (0, 0)
frame_count = 0
fps_timer = time.time()
fps = 0
rec_ms = 0
last_probe_time = time.time()

try:
    while True:
        # 1. Hotplug probe every 1.0 second
        if time.time() - last_probe_time >= 1.0:
            last_probe_time = time.time()
            try:
                cur_devs = discover_capture_devices()
                active_paths = [c["path"] for c in caps]
                for dev_info in cur_devs:
                    if dev_info["path"] not in active_paths:
                        new_c = open_single_camera(dev_info, fw=640, fh=480)
                        if new_c:
                            caps.append(new_c)
                            print(f"\033[92m[Howdy Test] Hotplug detected! Armed new camera: {new_c['name']} ({new_c['path']})\033[0m")
            except Exception:
                pass

        # 2. Capture and process frames from all active cameras
        processed_frames = []
        dead_cams = []

        for cam in caps:
            try:
                ret, frame = cam["cap"].read()
            except Exception:
                ret, frame = False, None

            if not ret or frame is None:
                dead_cams.append(cam)
                continue

            if frame.shape[1] != TILE_W or frame.shape[0] != TILE_H:
                frame = cv2.resize(frame, (TILE_W, TILE_H), interpolation=cv2.INTER_AREA)

            h, w = frame.shape[:2]
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            t0 = time.time()
            faces = detector(rgb_frame, 0)
            rec_ms = int((time.time() - t0) * 1000)

            # Camera label badge
            cv2.rectangle(frame, (10, 10), (10 + len(cam["name"]) * 11, 35), (20, 20, 20), cv2.FILLED)
            cv2.putText(frame, f"[{cam['name'].upper()}]", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

            for rect in faces:
                x1, y1, x2, y2 = rect.left(), rect.top(), rect.right(), rect.bottom()
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

                if is_match:
                    hud_color = (0, 255, 64)
                    title_text = f"MATCH: {user.upper()} [AUTHENTICATED]"
                    sub_text = f"Certainty: {best_dist:.2f} (Model #{best_id}: {best_label})"
                else:
                    hud_color = (48, 48, 255)
                    title_text = "UNKNOWN FACE [ACCESS DENIED]"
                    sub_text = f"Distance: {best_dist:.2f} (Threshold: {certainty_threshold})"

                line_len = int((x2 - x1) * 0.25)
                thick = 2
                cv2.line(frame, (x1, y1), (x1 + line_len, y1), hud_color, thick)
                cv2.line(frame, (x1, y1), (x1, y1 + line_len), hud_color, thick)
                cv2.line(frame, (x2, y1), (x2 - line_len, y1), hud_color, thick)
                cv2.line(frame, (x2, y1), (x2, y1 + line_len), hud_color, thick)
                cv2.line(frame, (x1, y2), (x1 + line_len, y2), hud_color, thick)
                cv2.line(frame, (x1, y2), (x1, y2 + line_len), hud_color, thick)
                cv2.line(frame, (x2, y2), (x2 - line_len, y2), hud_color, thick)
                cv2.line(frame, (x2, y2), (x2, y2 - line_len), hud_color, thick)

                cv2.rectangle(frame, (x1, max(0, y1 - 25)), (x1 + len(title_text) * 10, y1), hud_color, cv2.FILLED)
                cv2.putText(frame, title_text, (x1 + 4, max(12, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1, cv2.LINE_AA)
                cv2.putText(frame, sub_text, (x1, min(h - 10, y2 + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, hud_color, 1, cv2.LINE_AA)

            processed_frames.append(frame)

        # 3. Handle hot-unplugged cameras
        if dead_cams:
            for dead in dead_cams:
                print(f"\033[93m[Howdy Test] Hot-unplug detected: Disconnected {dead['name']} ({dead['path']})\033[0m")
                try:
                    dead["cap"].release()
                except Exception:
                    pass
                if dead in caps:
                    caps.remove(dead)

        # 4. FPS counter
        frame_count += 1
        if time.time() - fps_timer >= 1.0:
            fps = frame_count
            frame_count = 0
            fps_timer = time.time()

        # 5. Build dynamic grid layout
        display_frame, target_w, target_h = build_hud_grid(
            processed_frames, caps, user, len(enrolled_vectors), certainty_threshold
        )

        if (target_w, target_h) != last_win_dims:
            cv2.resizeWindow(WIN_NAME, target_w, target_h)
            last_win_dims = (target_w, target_h)

        # Telemetry bottom bar
        dh, dw = display_frame.shape[:2]
        cv2.rectangle(display_frame, (0, dh - 35), (dw, dh), (10, 10, 10), cv2.FILLED)
        info_str = f"MULTI-CAMERA HUD ({len(caps)} ARMED) | FPS: {fps} | LATENCY: {rec_ms}ms | ENROLLED: {len(enrolled_vectors)} | CERTAINTY: {certainty_threshold}"
        cv2.putText(display_frame, info_str, (15, dh - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

        cv2.imshow(WIN_NAME, display_frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break

finally:
    for cam in caps:
        try:
            cam["cap"].release()
        except Exception:
            pass
    cv2.destroyAllWindows()
    print("[Howdy Test] Multi-camera diagnostic session closed.")
