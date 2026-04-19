"""
=============================================================================
camera_demo.py  —  "How does the car SEE?" classroom demo
=============================================================================
Run this on any laptop with a webcam. No Arduino, no Bluetooth, no car needed.

Shows kids exactly what the car's camera sees and how the computer
recognises objects in real time — the same technology inside the car.

HOW TO RUN
----------
  pip install opencv-python ultralytics
  python camera_demo.py

CONTROLS (press while the window is open)
------------------------------------------
  SPACE  —  pause / unpause the camera feed
  +  /  -  —  raise / lower the confidence threshold live
  Q  —  quit

WHAT KIDS WILL SEE
-------------------
  • Live camera feed from the laptop webcam
  • Coloured boxes drawn around every recognised object
  • Object name + confidence % inside each box
  • Big "WOULD STOP" banner when a trigger object is close enough
  • A running count of detections this session
  • FPS counter so they can see how fast the computer is "thinking"
=============================================================================
"""

import cv2
import time
import sys
import numpy as np

# ── YOLO trigger objects (same list as the car) ───────────────────────────
TRIGGER_CLASSES = {
    0:  "Person",
    1:  "Bicycle",
    2:  "Car",
    15: "Cat",
    16: "Dog",
    56: "Chair",
    57: "Couch",
    60: "Table",
}

# Colours per object type (BGR) — kids can see different boxes for different things
CLASS_COLOURS = {
    "Person":  (0,   80, 230),   # red-orange
    "Bicycle": (0,  180,  60),   # green
    "Car":     (200, 60,   0),   # blue
    "Cat":     (180,  0, 180),   # purple
    "Dog":     (0,  160, 210),   # amber
    "Chair":   (0,  200, 200),   # yellow
    "Couch":   (60, 180, 100),   # teal
    "Table":   (100, 60, 200),   # coral
}
DEFAULT_COLOUR = (180, 180, 180)

# How large a bounding box has to be (fraction of frame area) before it
# triggers a "WOULD STOP" — prevents distant tiny objects triggering it
CLOSE_THRESHOLD = 0.06   # 6 % of total frame area


def load_yolo():
    """Load YOLOv8-nano with a friendly progress message."""
    try:
        from ultralytics import YOLO
        print()
        print("  Loading AI model (downloads ~6 MB first time, then instant)...")
        model = YOLO("yolov8n.pt")
        print("  Model ready!\n")
        return model
    except ImportError:
        print("\n  ERROR: ultralytics not installed.")
        print("  Run:  pip install ultralytics\n")
        sys.exit(1)


def open_camera(index: int = 0):
    """Open the default webcam with a clear error if unavailable."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"\n  ERROR: Could not open camera (device {index}).")
        print("  Try: python camera_demo.py  (or check your webcam connection)\n")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def read_frame_with_retry(cap, retries: int = 10, delay_s: float = 0.05):
    """Read one frame, retrying briefly for transient webcam hiccups."""
    for _ in range(retries):
        ret, frame = cap.read()
        if ret and frame is not None:
            return True, frame
        time.sleep(delay_s)
    return False, None


def is_close(box, frame_w, frame_h) -> bool:
    """True if the bounding box is large enough to mean 'close and blocking'."""
    _, _, w, h = box
    box_area   = w * h
    frame_area = frame_w * frame_h
    return (box_area / frame_area) >= CLOSE_THRESHOLD


def draw_frame(frame, detections, confidence, paused, fps, total_count):
    """
    Draw everything onto one frame:
      • Bounding boxes + labels
      • Top status bar (FPS, confidence, pause state)
      • "WOULD STOP" banner if something close is detected
      • Bottom legend strip
    """
    h, w = frame.shape[:2]

    # ── Bounding boxes ────────────────────────────────────────────────────
    would_stop   = False
    trigger_names = []

    for det in detections:
        label = det["label"]
        conf  = det["conf"]
        x, y, bw, bh = det["box"]

        colour = CLASS_COLOURS.get(label, DEFAULT_COLOUR)
        close  = is_close(det["box"], w, h)

        # Thicker border if object is close / would trigger a stop
        thickness = 3 if close else 2
        cv2.rectangle(frame, (x, y), (x + bw, y + bh), colour, thickness)

        # Label pill
        tag = f"{label}  {conf:.0%}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        (lw, lh), _ = cv2.getTextSize(tag, font, 0.55, 2)
        pill_top = max(0, y - lh - 10)
        cv2.rectangle(frame, (x, pill_top), (x + lw + 12, y), colour, -1)
        cv2.putText(frame, tag, (x + 6, y - 4), font, 0.55, (255, 255, 255), 2)

        if close and label in [v for v in TRIGGER_CLASSES.values()]:
            would_stop = True
            trigger_names.append(label)

    # ── "WOULD STOP" banner ───────────────────────────────────────────────
    if would_stop:
        names = " & ".join(sorted(set(trigger_names)))
        banner = f"  WOULD STOP  —  {names} IS CLOSE  "
        font = cv2.FONT_HERSHEY_DUPLEX
        (bw2, bh2), _ = cv2.getTextSize(banner, font, 0.75, 2)
        by = h // 2 - bh2 // 2

        # Semi-transparent red overlay behind banner
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, by - 14), (w, by + bh2 + 14), (0, 0, 180), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Banner text
        cv2.putText(frame, banner,
                    ((w - bw2) // 2 + 1, by + bh2 + 1),
                    font, 0.75, (0, 0, 0), 3)
        cv2.putText(frame, banner,
                    ((w - bw2) // 2, by + bh2),
                    font, 0.75, (255, 255, 255), 2)

    # ── Top status bar ────────────────────────────────────────────────────
    bar_h = 36
    cv2.rectangle(frame, (0, 0), (w, bar_h), (18, 18, 18), -1)

    font_s = cv2.FONT_HERSHEY_SIMPLEX
    pause_text = "  PAUSED — press SPACE"  if paused else ""

    cv2.putText(frame, f"FPS: {fps:4.1f}",
                (8, 24), font_s, 0.55, (140, 140, 140), 1)
    cv2.putText(frame, f"Confidence: {confidence:.0%}   (+/-  to adjust)",
                (90, 24), font_s, 0.55, (140, 140, 140), 1)
    cv2.putText(frame, f"Objects seen today: {total_count}",
                (360, 24), font_s, 0.55, (140, 200, 140), 1)
    if pause_text:
        cv2.putText(frame, pause_text, (w // 2 - 120, 24),
                    font_s, 0.55, (0, 200, 255), 2)

    # ── Bottom legend ─────────────────────────────────────────────────────
    leg_y = h - 22
    cv2.rectangle(frame, (0, h - 30), (w, h), (18, 18, 18), -1)

    legend_items = [
        ("Person / Animal / Vehicle / Furniture", (200, 200, 200)),
        ("  ←  things the car can recognise", (100, 100, 100)),
    ]
    lx = 8
    for txt, col in legend_items:
        cv2.putText(frame, txt, (lx, leg_y), font_s, 0.45, col, 1)
        (tw, _), _ = cv2.getTextSize(txt, font_s, 0.45, 1)
        lx += tw + 6

    # Press Q hint
    cv2.putText(frame, "Q = quit",
                (w - 76, leg_y), font_s, 0.45, (80, 80, 80), 1)

    return frame


def print_startup_message():
    print()
    print("=" * 58)
    print("   Safety Car — Camera Demo")
    print("   How does the car SEE?")
    print("=" * 58)
    print()
    print("  The camera looks at the world.")
    print("  The AI finds objects and draws boxes around them.")
    print("  When something is close, the car would STOP.")
    print()
    print("  CONTROLS")
    print("  ─────────────────────────────────────────")
    print("  SPACE    pause / unpause")
    print("  +        make detection more sensitive")
    print("  -        make detection less sensitive")
    print("  Q        quit")
    print()
    print("  Starting camera...")
    print()


def main():
    print_startup_message()

    model  = load_yolo()
    cap    = open_camera(0)

    confidence   = 0.50     # starting detection threshold
    paused       = False
    total_count  = 0        # cumulative distinct detections this session

    # FPS tracking
    fps          = 0.0
    frame_times  = []

    last_frame   = None     # kept so we can display while paused
    read_failures = 0

    print("  Camera open. Showing window now...")
    print("  (Close the window or press Q to quit)\n")

    while True:
        # ── Read frame ────────────────────────────────────────────────────
        if not paused:
            ret, frame = read_frame_with_retry(cap)
            if not ret:
                read_failures += 1
                if read_failures == 1:
                    print("  Camera temporarily unavailable — retrying...")
                if read_failures >= 5:
                    print("  Camera read failed repeatedly — exiting.")
                    break
                continue
            read_failures = 0
            last_frame = frame.copy()
        else:
            frame = last_frame.copy() if last_frame is not None else \
                    np.zeros((480, 640, 3), dtype=np.uint8)

        # ── FPS ───────────────────────────────────────────────────────────
        now = time.time()
        frame_times.append(now)
        frame_times = [t for t in frame_times if now - t <= 1.0]
        fps = len(frame_times)

        # ── YOLO detection ────────────────────────────────────────────────
        detections = []
        if not paused:
            results = model(frame, verbose=False, conf=confidence)
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    if cls_id not in TRIGGER_CLASSES:
                        continue
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    detections.append({
                        "label": TRIGGER_CLASSES[cls_id],
                        "box":   (x1, y1, x2 - x1, y2 - y1),
                        "conf":  float(box.conf[0]),
                    })
            total_count += len(detections)

        # ── Draw ──────────────────────────────────────────────────────────
        display = draw_frame(
            frame, detections, confidence, paused, fps, total_count
        )
        cv2.imshow("Safety Car — Camera Demo  (Q to quit)", display)

        # ── Key handling ──────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:        # Q or ESC
            print("\n  Closing demo. See you next time!")
            break

        elif key == ord(" "):                   # SPACE — pause/unpause
            paused = not paused
            print("  PAUSED" if paused else "  RESUMED")

        elif key == ord("+") or key == ord("="):  # raise sensitivity
            confidence = max(0.10, confidence - 0.05)
            print(f"  Confidence threshold → {confidence:.0%}")

        elif key == ord("-"):                   # lower sensitivity
            confidence = min(0.95, confidence + 0.05)
            print(f"  Confidence threshold → {confidence:.0%}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
