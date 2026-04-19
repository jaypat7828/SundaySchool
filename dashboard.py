"""
=============================================================================
Dashboard — OpenCV live display for the Safety Car
=============================================================================

LAYOUT (640 × 480 window)
--------------------------

  ┌──────────────────────────────────────────┐  ← y=0
  │           STATUS BAR  (70 px)            │  big colour + text
  │  GREEN=safe  YELLOW=warning  RED=stopped │
  │  [████████░░░░░░░░░░] countdown bar      │
  ├──────────────────────────────────────────┤  ← y=70
  │                                          │
  │        LIVE CAMERA FEED  (360 px)        │
  │    bounding boxes + object labels        │
  │                                          │
  ├──────────────────────────────────────────┤  ← y=430
  │  BLUETOOTH: FORWARD │ STATUS │ DETECTED  │  info row (50 px)
  └──────────────────────────────────────────┘  ← y=480
=============================================================================
"""

import cv2
import numpy as np

# BGR colour constants
_GREEN  = (34,  180,  34)
_YELLOW = (0,   200, 255)
_RED    = (0,    40, 210)
_WHITE  = (255, 255, 255)
_BLACK  = (0,     0,   0)
_DARK   = (28,   28,  28)
_GREY   = (60,   60,  60)
_LGREY  = (140, 140, 140)

# Human-readable label for each Bluetooth command char
_BT_LABELS = {
    "F": "FORWARD",    "B": "BACKWARD",
    "L": "LEFT",       "R": "RIGHT",
    "G": "FWD-LEFT",   "I": "FWD-RIGHT",
    "H": "BCK-LEFT",   "J": "BCK-RIGHT",
    "S": "STOP",       "W": "LED ON",  "w": "LED OFF",
}


class Dashboard:
    """Renders the safety car live display into an OpenCV window."""

    W        = 640    # total window width
    STATUS_H = 70     # status bar height
    CAM_H    = 360    # camera feed height
    INFO_H   = 50     # info row height
    TOTAL_H  = STATUS_H + CAM_H + INFO_H   # 480

    def __init__(self, window_name: str = "Safety Car  |  press Q to quit"):
        self.window_name = window_name
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    # ------------------------------------------------------------------
    # Public — call once per frame
    # ------------------------------------------------------------------

    def render(
        self,
        frame,              # BGR numpy array from camera (or None)
        detections: list,   # list of {"label":str, "box":(x,y,w,h), "conf":float}
        state: str,         # "CLEAR" | "WARNING" | "STOPPED"
        bt_command: str,    # latest Bluetooth command char e.g. "F"
        warning_progress: float,  # 0.0–1.0
    ) -> int:
        """
        Draw the full dashboard and display it.

        Returns the cv2.waitKey(1) keycode so the caller can detect 'q'.
        """
        canvas = np.full((self.TOTAL_H, self.W, 3), _DARK, dtype=np.uint8)

        self._draw_status_bar(canvas, state, detections, warning_progress)
        self._draw_camera(canvas, frame, detections)
        self._draw_info_row(canvas, state, bt_command, detections)

        cv2.imshow(self.window_name, canvas)
        return cv2.waitKey(1) & 0xFF

    # ------------------------------------------------------------------
    # Status bar — top band, changes colour with state
    # ------------------------------------------------------------------

    def _draw_status_bar(self, canvas, state, detections, progress):
        y, h = 0, self.STATUS_H

        if state == "CLEAR":
            bg    = _GREEN
            label = "ALL CLEAR  —  PATH IS SAFE"
        elif state == "WARNING":
            bg     = _YELLOW
            secs   = max(0.0, 2.0 - progress * 2.0)
            labels = "  &  ".join(sorted(set(d["label"] for d in detections)))
            label  = f"WARNING: {labels}  —  STOPPING IN {secs:.1f}s"
        else:   # STOPPED
            bg     = _RED
            labels = "  &  ".join(sorted(set(d["label"] for d in detections)))
            label  = f"STOPPED  —  {labels} IN THE WAY"

        # Coloured background
        cv2.rectangle(canvas, (0, y), (self.W, y + h), bg, -1)

        # Centred bold text — draw twice (black shadow then white) for contrast
        font, scale, thick = cv2.FONT_HERSHEY_DUPLEX, 0.70, 2
        (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
        tx = max(8, (self.W - tw) // 2)
        ty = y + (h - 8) // 2 + th // 2
        cv2.putText(canvas, label, (tx + 1, ty + 1), font, scale, _BLACK, thick + 1)
        cv2.putText(canvas, label, (tx,     ty),     font, scale, _WHITE, thick)

        # Progress bar — depletes left→right during WARNING
        if state == "WARNING":
            bar_y = y + h - 7
            cv2.rectangle(canvas, (0, bar_y), (self.W, y + h), (0, 130, 180), -1)
            fill_w = int(self.W * progress)
            cv2.rectangle(canvas, (0, bar_y), (fill_w, y + h), (0, 50, 240), -1)

    # ------------------------------------------------------------------
    # Camera feed — centre section
    # ------------------------------------------------------------------

    def _draw_camera(self, canvas, frame, detections):
        y0 = self.STATUS_H

        if frame is None:
            # Placeholder when camera not available
            cy = y0 + self.CAM_H // 2
            cv2.putText(canvas, "No camera feed",
                        (215, cy), cv2.FONT_HERSHEY_SIMPLEX,
                        0.9, (80, 80, 80), 2)
            return

        # Resize frame to fit camera area
        cam = cv2.resize(frame, (self.W, self.CAM_H))

        # Scale factors for bounding box coordinates
        sx = self.W / frame.shape[1]
        sy = self.CAM_H / frame.shape[0]

        for det in detections:
            ox, oy, ow, oh = det["box"]
            bx  = int(ox * sx);  by  = int(oy * sy)
            bx2 = int((ox + ow) * sx);  by2 = int((oy + oh) * sy)

            # Red bounding box
            cv2.rectangle(cam, (bx, by), (bx2, by2), (0, 0, 255), 2)

            # Label pill above the box
            tag  = f"{det['label']}  {det['conf']:.0%}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (lw, lh), _ = cv2.getTextSize(tag, font, 0.55, 2)
            pill_y1 = max(0, by - lh - 10)
            pill_y2 = by
            cv2.rectangle(cam, (bx, pill_y1), (bx + lw + 10, pill_y2), (0, 0, 200), -1)
            cv2.putText(cam, tag, (bx + 5, by - 4), font, 0.55, _WHITE, 2)

        canvas[y0 : y0 + self.CAM_H] = cam

    # ------------------------------------------------------------------
    # Info row — bottom band
    # ------------------------------------------------------------------

    def _draw_info_row(self, canvas, state, bt_command, detections):
        y0 = self.STATUS_H + self.CAM_H

        # Dark background + divider line
        cv2.rectangle(canvas, (0, y0), (self.W, self.TOTAL_H), (18, 18, 18), -1)
        cv2.line(canvas, (0, y0), (self.W, y0), _GREY, 1)

        font = cv2.FONT_HERSHEY_SIMPLEX
        label_y = y0 + 16   # small label row
        value_y = y0 + 38   # big value row

        # --- Column 1: Bluetooth direction ---
        bt_text = _BT_LABELS.get(bt_command, bt_command or "—")
        cv2.putText(canvas, "BLUETOOTH",  (20, label_y), font, 0.38, _LGREY, 1)
        cv2.putText(canvas, bt_text,      (20, value_y), font, 0.65, _WHITE, 2)

        # Vertical divider
        cv2.line(canvas, (self.W // 3, y0 + 8), (self.W // 3, self.TOTAL_H - 8), _GREY, 1)

        # --- Column 2: Car safety state ---
        state_color = {"CLEAR": _GREEN, "WARNING": _YELLOW, "STOPPED": _RED}.get(state, _WHITE)
        x2 = self.W // 3 + 16
        cv2.putText(canvas, "CAR STATE", (x2, label_y), font, 0.38, _LGREY, 1)
        cv2.putText(canvas, state,       (x2, value_y), font, 0.65, state_color, 2)

        # Vertical divider
        cv2.line(canvas, (2 * self.W // 3, y0 + 8), (2 * self.W // 3, self.TOTAL_H - 8), _GREY, 1)

        # --- Column 3: Detected objects ---
        obj_text = ", ".join(sorted(set(d["label"] for d in detections))) if detections else "None"
        x3 = 2 * self.W // 3 + 16
        cv2.putText(canvas, "DETECTED",       (x3, label_y), font, 0.38, _LGREY, 1)
        cv2.putText(canvas, obj_text[:20],    (x3, value_y), font, 0.55, _WHITE, 1)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        cv2.destroyWindow(self.window_name)
