#!/usr/bin/env python3
# ==============================================================================
# HOWDY LIVE HUD INTERACTIVE BIOMETRIC SCAN ENROLLMENT ENGINE
# Renders a real-time Sci-Fi Biometric HUD while continuously capturing,
# quality-filtering, and enrolling high-precision facial descriptors
# across multiple cameras, angles, distances, and lighting conditions.
# ==============================================================================

import os
import sys
import time
import json
import glob
import re
import signal
import configparser
import dlib
import cv2
import numpy as np
import concurrent.futures

howdy_dir = "/lib/security/howdy"
if not os.path.isdir(howdy_dir):
    howdy_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, howdy_dir)
from recorders.video_capture import discover_capture_devices, open_single_camera
import security
import vision_engine

vision_engine.lock_process_memory()

config = configparser.ConfigParser()
config.read(os.path.join(howdy_dir, "config.ini"))
certainty_threshold = config.getfloat("video", "certainty", fallback=3.5)
user = os.getenv("SUDO_USER") or os.getenv("USER") or "mr-reaper"

# Hardware acceleration telemetry
accel_badge = vision_engine.get_hardware_acceleration_badge()

# Load existing models
existing_models = security.load_user_models(user)
enrolled_vectors = []
for m in existing_models:
    for vec in m.get("data", []):
        if len(vec) == 128:
            enrolled_vectors.append(vec)

known_matrix = np.array(enrolled_vectors) if enrolled_vectors else None

# Discover and open all active cameras
candidates = discover_capture_devices()
with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(candidates))) as executor:
    results = list(executor.map(lambda c: open_single_camera(c, fw=640, fh=480), candidates))
caps = [c for c in results if c is not None]

if not caps:
    print("[Error] No cameras available for enrollment.", file=sys.stderr)
    sys.exit(1)

print("\n==================================================================")
print("     HOWDY LIVE HUD INTERACTIVE BIOMETRIC ENROLLMENT ENGINE       ")
print("==================================================================")
print(f"• Active Target User: {user}")
print(f"• Initial Enrolled Vault: {len(existing_models)} models (AES-256-GCM)")
print(f"• Compute Hardware: {accel_badge}")
print(f"• Armed Cameras ({len(caps)} active concurrently):")
for idx, c in enumerate(caps):
    print(f"    [{idx + 1}] {c['name']} ({c['path']})")
print("• Live Visual HUD: Active on display")
print("• Controls: Move head across varied angles, tilts, distances")
print("• Finish: Click [X CLOSE] or press 'q' / ESC at any time")
print("==================================================================\n")

# Initialize models
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(os.path.join(howdy_dir, "dlib-data", "shape_predictor_5_face_landmarks.dat"))
encoder = dlib.face_recognition_model_v1(os.path.join(howdy_dir, "dlib-data", "dlib_face_recognition_resnet_model_v1.dat"))

yunet_path = os.path.join(howdy_dir, "models", "face_detection_yunet_2023mar.onnx")
yunet_detector = vision_engine.ONNXYuNetDetector(yunet_path)

liveness_path = os.path.join(howdy_dir, "models", "minifasnet_v2.onnx")
liveness_verifier = vision_engine.PassiveLivenessVerifier(liveness_path)

haar_path = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_alt2.xml"
haar_detector = cv2.CascadeClassifier(haar_path) if os.path.isfile(haar_path) else None

WIN_NAME = "Howdy Live Biometric HUD & Facial Enrollment"
cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)

TILE_W = 640
TILE_H = 480

exit_requested = False
btn_bounds = [0, 0, 0, 0]

def on_mouse(event, x, y, flags, param):
    global exit_requested
    if event == cv2.EVENT_LBUTTONDOWN:
        if (btn_bounds[0] <= x <= btn_bounds[2]) and (btn_bounds[1] <= y <= btn_bounds[3]):
            exit_requested = True

cv2.setMouseCallback(WIN_NAME, on_mouse)

def sig_handler(sig, frame):
    global exit_requested
    exit_requested = True

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

# Enrollment Configuration
TARGET_NEW_SAMPLES = 50
new_samples = []
last_capture_time = {c["name"]: 0.0 for c in caps}
capture_flash = {c["name"]: 0.0 for c in caps}
cam_sample_count = {c["name"]: 0 for c in caps}
enrollment_complete = False
target_per_camera = max(1, TARGET_NEW_SAMPLES // len(caps))

def draw_biometric_hud(frame, rect, shape, is_match, best_dist, cert_thresh, light_text, light_color, det_text, liveness_pct, is_live, blur_score, flash_active, sample_num):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = rect.left(), rect.top(), rect.right(), rect.bottom()
    hud_color = (0, 255, 64) if (is_match and is_live) else (48, 48, 255)

    if flash_active:
        hud_color = (0, 255, 255) # Cyan/Yellow flash on capture
        cv2.rectangle(frame, (5, 5), (w - 5, h - 5), (0, 255, 255), 3)
        cv2.putText(frame, f"[+ ENROLLED SAMPLE #{sample_num}]", (w // 2 - 130, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)

    # 1. Corner Reticle Brackets
    bracket_len = int((x2 - x1) * 0.22)
    thick = 2
    cv2.line(frame, (x1, y1), (x1 + bracket_len, y1), hud_color, thick)
    cv2.line(frame, (x1, y1), (x1, y1 + bracket_len), hud_color, thick)
    cv2.line(frame, (x2, y1), (x2 - bracket_len, y1), hud_color, thick)
    cv2.line(frame, (x2, y1), (x2, y1 + bracket_len), hud_color, thick)
    cv2.line(frame, (x1, y2), (x1 + bracket_len, y2), hud_color, thick)
    cv2.line(frame, (x1, y2), (x1, y2 - bracket_len), hud_color, thick)
    cv2.line(frame, (x2, y2), (x2 - bracket_len, y2), hud_color, thick)
    cv2.line(frame, (x2, y2), (x2, y2 - bracket_len), hud_color, thick)

    # 2. Constellation Mesh
    pts = [(shape.part(i).x, shape.part(i).y) for i in range(shape.num_parts)]
    if len(pts) >= 5:
        cv2.line(frame, pts[0], pts[1], (0, 240, 220), 1, cv2.LINE_AA)
        cv2.line(frame, pts[1], pts[2], (0, 200, 255), 1, cv2.LINE_AA)
        cv2.line(frame, pts[2], pts[3], (0, 240, 220), 1, cv2.LINE_AA)
        cv2.line(frame, pts[0], pts[4], (0, 180, 255), 1, cv2.LINE_AA)
        cv2.line(frame, pts[1], pts[4], (0, 220, 255), 1, cv2.LINE_AA)
        cv2.line(frame, pts[2], pts[4], (0, 220, 255), 1, cv2.LINE_AA)
        cv2.line(frame, pts[3], pts[4], (0, 180, 255), 1, cv2.LINE_AA)
        for p in pts:
            cv2.circle(frame, p, 3, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, p, 6, (0, 200, 100), 1, cv2.LINE_AA)
        cv2.drawMarker(frame, pts[4], (0, 255, 255), markerType=cv2.MARKER_CROSS, markerSize=12, thickness=1)

    # 3. Upper Status Banner
    bx1 = max(10, x1)
    by1 = max(28, y1 - 10)
    title_text = f"TARGET: {user.upper()} [TRACKING]"
    banner_w = max(220, len(title_text) * 10)
    cv2.rectangle(frame, (bx1, by1 - 20), (bx1 + banner_w, by1), hud_color, cv2.FILLED)
    cv2.putText(frame, title_text, (bx1 + 6, by1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1, cv2.LINE_AA)

    # 4. Telemetry Badges
    ly = min(h - 75, y2 + 18)
    cv2.rectangle(frame, (bx1, ly - 14), (bx1 + 240, ly + 2), (20, 20, 20), cv2.FILLED)
    cv2.rectangle(frame, (bx1, ly - 14), (bx1 + 240, ly + 2), light_color, 1)
    cv2.putText(frame, f"LIGHT: {light_text}", (bx1 + 5, ly - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.34, light_color, 1, cv2.LINE_AA)

    ly += 18
    cv2.rectangle(frame, (bx1, ly - 14), (bx1 + 240, ly + 2), (20, 20, 20), cv2.FILLED)
    cv2.rectangle(frame, (bx1, ly - 14), (bx1 + 240, ly + 2), (200, 100, 255), 1)
    cv2.putText(frame, f"BACKBONE: {det_text}", (bx1 + 5, ly - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (220, 150, 255), 1, cv2.LINE_AA)

    ly += 18
    sharp_col = (0, 255, 128) if blur_score >= 60 else (0, 150, 255)
    cv2.rectangle(frame, (bx1, ly - 14), (bx1 + 240, ly + 2), (20, 20, 20), cv2.FILLED)
    cv2.rectangle(frame, (bx1, ly - 14), (bx1 + 240, ly + 2), sharp_col, 1)
    cv2.putText(frame, f"SHARPNESS: {blur_score:.1f} (LIVENESS: {liveness_pct:.1f}%)", (bx1 + 5, ly - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.33, sharp_col, 1, cv2.LINE_AA)


last_win_dims = (0, 0)
fps_timer = time.time()
frame_count = 0
fps = 0

try:
    while not exit_requested:
        try:
            vis_prop = cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE)
            auto_prop = cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_AUTOSIZE)
            if vis_prop <= 0 or auto_prop < 0:
                break
        except Exception:
            break

        processed_frames = []

        for cam in caps:
            cname = cam["name"]
            try:
                ret, frame = cam["cap"].read()
            except Exception:
                ret, frame = False, None

            if not ret or frame is None:
                continue

            if frame.shape[1] != TILE_W or frame.shape[0] != TILE_H:
                frame = cv2.resize(frame, (TILE_W, TILE_H), interpolation=cv2.INTER_AREA)

            # MSRCR Dynamic Photometric Preprocessing
            enh_frame, enh_gs, light_label, light_col = vision_engine.adaptive_photometric_preprocess(frame)

            # Multi-Backbone Face Detection Cascade
            face_locations = []
            det_label = "NONE"

            if yunet_detector.available:
                yn_faces = yunet_detector.detect(enh_frame)
                if yn_faces:
                    face_locations = [f["rect"] for f in yn_faces]
                    det_label = "YUNET CNN (+-85 YAW)"

            if len(face_locations) == 0:
                hog_faces = detector(enh_gs, 1)
                if len(hog_faces) > 0:
                    face_locations = hog_faces
                    det_label = "DLIB HOG (GRADIENT)"

            if len(face_locations) == 0 and haar_detector is not None:
                haar_boxes = haar_detector.detectMultiScale(enh_gs, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
                if len(haar_boxes) > 0:
                    face_locations = [dlib.rectangle(int(hx), int(hy), int(hx + hw), int(hy + hh)) for (hx, hy, hw, hh) in haar_boxes]
                    det_label = "HAAR CASCADE"

            # Camera label banner
            cv2.rectangle(frame, (10, 10), (10 + len(cname) * 11, 35), (20, 20, 20), cv2.FILLED)
            cv2.putText(frame, f"[{cname.upper()}] ({cam_sample_count[cname]}/{target_per_camera})", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)

            # Calculate sharpness score
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            flash_on = (time.time() - capture_flash[cname] < 0.35)

            for rect in face_locations:
                liveness_pct = 100.0
                is_live = True
                if liveness_verifier.available:
                    liveness_score, is_live = liveness_verifier.verify(enh_frame, rect)
                    liveness_pct = liveness_score * 100.0

                shape = predictor(enh_frame, rect)

                # Check if eligible for new sample enrollment
                now = time.time()
                can_capture = (
                    not enrollment_complete and
                    len(new_samples) < TARGET_NEW_SAMPLES and
                    cam_sample_count[cname] < target_per_camera and
                    (now - last_capture_time[cname] >= 0.38) and
                    blur_score >= 45.0 and
                    is_live
                )

                if can_capture:
                    face_desc = np.array(encoder.compute_face_descriptor(enh_frame, shape, num_jitters=2))
                    sample_id = len(existing_models) + len(new_samples)
                    cam_clean = "Brio 100" if "Brio" in cname else "Integrated FHD"
                    lbl = f"{cam_clean} #{sample_id + 1}"

                    new_samples.append({
                        "id": sample_id,
                        "label": lbl,
                        "data": [face_desc.tolist()]
                    })
                    cam_sample_count[cname] += 1
                    last_capture_time[cname] = now
                    capture_flash[cname] = now
                    flash_on = True

                    print(f"  [✓] Enrolled sample #{len(new_samples)}/{TARGET_NEW_SAMPLES}: {lbl} ({cname})")

                    # Check if target reached
                    if len(new_samples) >= TARGET_NEW_SAMPLES:
                        enrollment_complete = True
                        all_models = existing_models + new_samples
                        security.save_user_models(user, all_models)
                        print(f"\n\033[92m[✓] ENROLLMENT COMPLETE: Sealed {len(new_samples)} new scans into AES-256-GCM vault!\033[0m")
                        print(f"\033[92m[✓] Total models now in vault: {len(all_models)}\033[0m\n")

                # Match against known matrix
                is_match = False
                best_dist = 99.0
                if known_matrix is not None and len(known_matrix) > 0:
                    face_desc_check = np.array(encoder.compute_face_descriptor(enh_frame, shape, num_jitters=1))
                    distances = np.linalg.norm(known_matrix - face_desc_check, axis=1) * 10.0
                    best_dist = np.min(distances)
                    if best_dist <= certainty_threshold:
                        is_match = True

                draw_biometric_hud(
                    frame, rect, shape, is_match, best_dist, certainty_threshold,
                    light_label, light_col, det_label, liveness_pct, is_live, blur_score,
                    flash_on, len(new_samples)
                )

            processed_frames.append(frame)

        # FPS
        frame_count += 1
        if time.time() - fps_timer >= 1.0:
            fps = frame_count
            frame_count = 0
            fps_timer = time.time()

        # Build grid
        if len(processed_frames) == 1:
            display_frame = processed_frames[0]
            target_w, target_h = TILE_W, TILE_H
        elif len(processed_frames) >= 2:
            display_frame = np.hstack([processed_frames[0], processed_frames[1]])
            target_w, target_h = TILE_W * 2, TILE_H
        else:
            display_frame = np.zeros((TILE_H, TILE_W, 3), dtype=np.uint8)
            target_w, target_h = TILE_W, TILE_H

        dh, dw = display_frame.shape[:2]

        # Top Enrollment Progress Bar
        total_vault_models = len(existing_models) + len(new_samples)
        cv2.rectangle(display_frame, (0, 0), (dw, 48), (15, 15, 15), cv2.FILLED)
        cv2.line(display_frame, (0, 48), (dw, 48), (40, 40, 40), 1)

        pct = min(1.0, len(new_samples) / float(TARGET_NEW_SAMPLES))
        prog_w = int((dw - 360) * pct)
        cv2.rectangle(display_frame, (20, 14), (dw - 340, 34), (30, 30, 30), cv2.FILLED)
        cv2.rectangle(display_frame, (20, 14), (20 + prog_w, 34), (0, 220, 100) if enrollment_complete else (255, 180, 0), cv2.FILLED)
        cv2.rectangle(display_frame, (20, 14), (dw - 340, 34), (80, 80, 80), 1)

        if not enrollment_complete:
            prog_text = f"ENROLLING SAMPLES: {len(new_samples)}/{TARGET_NEW_SAMPLES} (Vault Total: {total_vault_models}) | Slowly turn head, tilt, smile, adjust distance"
        else:
            prog_text = f"ENROLLMENT COMPLETE! {len(new_samples)} SAMPLES SAVED TO VAULT (Total: {total_vault_models}) | Press SPACE for 50 more"

        cv2.putText(display_frame, prog_text, (28, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)

        # Top-Right [X CLOSE / EXIT] button
        btn_w, btn_h = 150, 32
        bx1 = dw - btn_w - 15
        by1 = 8
        bx2 = bx1 + btn_w
        by2 = by1 + btn_h
        btn_bounds = [bx1, by1, bx2, by2]

        cv2.rectangle(display_frame, (bx1, by1), (bx2, by2), (40, 20, 180), cv2.FILLED)
        cv2.rectangle(display_frame, (bx1, by1), (bx2, by2), (80, 50, 255), 2)
        cv2.putText(display_frame, "[X] CLOSE / EXIT", (bx1 + 12, by1 + 21), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        # Bottom Bar
        cv2.rectangle(display_frame, (0, dh - 32), (dw, dh), (10, 10, 10), cv2.FILLED)
        b_str = f"LIVE MULTI-CAMERA HUD ({len(caps)} SENSORS) | FPS: {fps} | COMPUTE: {accel_badge} | [X] or 'q' to FINISH"
        cv2.putText(display_frame, b_str, (15, dh - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)

        if (target_w, target_h) != last_win_dims:
            cv2.resizeWindow(WIN_NAME, target_w, target_h)
            last_win_dims = (target_w, target_h)

        cv2.imshow(WIN_NAME, display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q'), ord('x'), ord('X')):
            break
        elif key == 32 and enrollment_complete:
            # Space pressed: capture another batch of 50!
            TARGET_NEW_SAMPLES += 50
            target_per_camera = max(1, TARGET_NEW_SAMPLES // len(caps))
            enrollment_complete = False
            print(f"\n>>> Extending target: Capturing 50 more samples (New Target: {TARGET_NEW_SAMPLES})...")

finally:
    for cam in caps:
        try:
            cam["cap"].release()
        except Exception:
            pass
    cv2.destroyAllWindows()
    for _ in range(10):
        cv2.waitKey(1)
    vision_engine.trim_heap_memory()
    print("[Howdy Scanner] Live enrollment HUD closed cleanly.")
