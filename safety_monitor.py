"""
=============================================================================
SafetyMonitor — YOLO detection + warning/stop state machine
=============================================================================

STATE MACHINE
-------------

              obstacle + forward cmd
  CLEAR  ─────────────────────────────►  WARNING
    ▲                                       │
    │  obstacle gone OR direction changed   │  2 seconds elapse
    │◄──────────────────────────────────────┘
    │                                       │
    │                                       ▼
    │  obstacle gone OR direction changed  STOPPED
    └──────────────────────────────────────────────

TRIGGER OBJECTS (COCO class IDs)
---------------------------------
  Only these classes trigger a warning — everything else is ignored.
  This prevents the car stopping for a distant coffee cup or phone.

  0  = Person        1  = Bicycle      2  = Car
  15 = Cat           16 = Dog
  56 = Chair         57 = Couch        60 = Dining table
=============================================================================
"""

import time
import logging
import numpy as np

logger = logging.getLogger(__name__)

# COCO class IDs that should trigger a safety warning
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

# Bluetooth commands that are pointing forward (camera direction)
FORWARD_COMMANDS = {"F", "G", "I"}


class SafetyMonitor:
    """
    Watches the camera, detects obstacles, and overrides the Arduino
    when the kid is driving toward something dangerous.
    """

    # State constants — also used by Dashboard for display
    CLEAR   = "CLEAR"
    WARNING = "WARNING"
    STOPPED = "STOPPED"

    def __init__(
        self,
        car,
        camera,
        warning_seconds: float = 2.0,
        confidence: float = 0.50,
    ):
        """
        Args:
            car:             ArduinoCar instance.
            camera:          VideoStream instance (already open).
            warning_seconds: How long to show warning before forcing a stop.
            confidence:      YOLO minimum confidence (0-1). 0.5 = 50%.
                             Lower = more sensitive (more false positives).
                             Higher = less sensitive (may miss things).
        """
        self.car = car
        self.camera = camera
        self.warning_seconds = warning_seconds
        self.confidence = confidence

        self.state = self.CLEAR
        self._warning_start = None      # time.time() when WARNING began
        self.current_detections = []    # latest list of detection dicts

        self._yolo = None
        self._load_yolo()

    # ------------------------------------------------------------------
    # YOLO setup
    # ------------------------------------------------------------------

    def _load_yolo(self):
        """
        Load YOLOv8-nano. Downloads ~6 MB on first run, then cached.
        Falls back gracefully if ultralytics isn't installed.
        """
        try:
            from ultralytics import YOLO
            logger.info("Loading YOLOv8-nano...")
            self._yolo = YOLO("yolov8n.pt")
            logger.info("YOLOv8-nano ready.")
        except ImportError:
            logger.error(
                "ultralytics not installed.\n"
                "Run: pip install ultralytics\n"
                "Detection will be disabled until installed."
            )
            self._yolo = None

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _detect(self, frame) -> list:
        """
        Run YOLO on one frame. Returns only trigger-class objects.

        Returns:
            List of dicts: {"label": str, "box": (x,y,w,h), "conf": float}
            Empty list if YOLO not loaded or nothing detected.
        """
        if self._yolo is None or frame is None:
            return []

        results = self._yolo(frame, verbose=False, conf=self.confidence)
        detections = []

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                if cls_id not in TRIGGER_CLASSES:
                    continue  # not a class we care about
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    "label": TRIGGER_CLASSES[cls_id],
                    "box":   (x1, y1, x2 - x1, y2 - y1),   # (x, y, w, h)
                    "conf":  float(box.conf[0]),
                })

        return detections

    # ------------------------------------------------------------------
    # Warning progress
    # ------------------------------------------------------------------

    def warning_progress(self) -> float:
        """
        How far through the warning countdown we are: 0.0 → 1.0.
        1.0 = 2 seconds elapsed = about to stop.
        Only meaningful when state == WARNING.
        """
        if self.state != self.WARNING or self._warning_start is None:
            return 0.0
        elapsed = time.time() - self._warning_start
        return min(elapsed / self.warning_seconds, 1.0)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def update(self, frame) -> tuple:
        """
        Process one frame. Call this in your main loop.

        Args:
            frame: BGR numpy array from VideoStream.read()

        Returns:
            (detections, state, warning_progress)
              detections      — list of detection dicts (may be empty)
              state           — "CLEAR", "WARNING", or "STOPPED"
              warning_progress — float 0.0–1.0 (only non-zero during WARNING)
        """
        # What is the kid pressing right now?
        bt_cmd = self.car.current_bt_command
        going_forward = bt_cmd in FORWARD_COMMANDS

        # Run YOLO
        detections = self._detect(frame)
        self.current_detections = detections
        obstacle_present = len(detections) > 0

        # --- CLEAR ---
        if self.state == self.CLEAR:
            if going_forward and obstacle_present:
                # Kid pressing forward + obstacle in view → start warning
                self.state = self.WARNING
                self._warning_start = time.time()
                labels = ", ".join(d["label"] for d in detections)
                logger.info("⚠ WARNING started — detected: %s", labels)

        # --- WARNING ---
        elif self.state == self.WARNING:
            if not obstacle_present or not going_forward:
                # Either obstacle cleared OR kid steered away — safe again
                self.state = self.CLEAR
                self._warning_start = None
                logger.info("✓ Warning cleared.")

            elif self.warning_progress() >= 1.0:
                # 2 seconds up — still heading toward obstacle → force stop
                self.state = self.STOPPED
                self.car.override_stop()
                labels = ", ".join(d["label"] for d in detections)
                logger.info("🛑 STOPPED — override sent. Obstacle: %s", labels)

        # --- STOPPED ---
        elif self.state == self.STOPPED:
            if not obstacle_present:
                # Obstacle is gone — resume
                self.state = self.CLEAR
                self.car.override_resume()
                logger.info("✓ Obstacle cleared — resuming Bluetooth control.")

            elif not going_forward:
                # Kid changed to a safe direction (reverse, turn, stop)
                # Lift override so Arduino can execute the new command
                self.state = self.CLEAR
                self.car.override_resume()
                logger.info("✓ Direction changed — resuming Bluetooth control.")

            # If still going forward + still obstacle: stay STOPPED, re-warn next iter

        return detections, self.state, self.warning_progress()
