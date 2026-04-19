"""
=============================================================================
vision_car_main.py  —  Safety Car Entry Point
=============================================================================

WHAT THIS RUNS
--------------
  • Connects to Arduino over USB serial
  • Opens DJI camera (USB webcam or Wi-Fi RTSP)
  • Starts YOLO safety monitor in the main loop
  • Renders live dashboard with camera feed + status

HOW TO RUN
----------
  # Default — USB camera, auto-detect Arduino port
  python vision_car_main.py

  # Specify Arduino port explicitly
  python vision_car_main.py --port COM5          (Windows)
  python vision_car_main.py --port /dev/ttyUSB0  (Linux)

  # Wi-Fi RTSP camera instead of USB
  python vision_car_main.py --camera rtsp

  # All options
  python vision_car_main.py --help

INSTALL
-------
  pip install pyserial opencv-python ultralytics

WHAT THE KID SEES
-----------------
  • GREEN bar  = safe, driving normally via Bluetooth phone app
  • YELLOW bar = obstacle detected, countdown starts (2 seconds)
  • RED bar    = car stopped, obstacle still in the way
  • Bar clears automatically when obstacle is removed or direction changes
=============================================================================
"""

import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="Safety Car — Bluetooth + CV obstacle detection")
    p.add_argument("--port",       default=None,
                   help="Arduino USB port (auto-detected if not given)")
    p.add_argument("--baud",       type=int, default=9600,
                   help="Serial baud rate (must match Arduino sketch)")
    p.add_argument("--camera",     choices=["usb", "rtsp"], default="usb",
                   help="usb = USB-C webcam mode | rtsp = Wi-Fi hotspot")
    p.add_argument("--device",     type=int, default=0,
                   help="USB camera device index (try 0, 1, 2)")
    p.add_argument("--rtsp",       default="rtsp://192.168.2.1/live",
                   help="RTSP URL for DJI Wi-Fi mode")
    p.add_argument("--width",      type=int, default=640)
    p.add_argument("--height",     type=int, default=480)
    p.add_argument("--confidence", type=float, default=0.50,
                   help="YOLO detection confidence threshold (0.0–1.0)")
    p.add_argument("--warning",    type=float, default=2.0,
                   help="Seconds of warning before forced stop")
    return p.parse_args()


def main():
    args = parse_args()

    from arduino_car   import ArduinoCar
    from dji_camera    import VideoStream
    from safety_monitor import SafetyMonitor
    from dashboard     import Dashboard

    # ── 1. Connect Arduino ───────────────────────────────────────────────
    car = ArduinoCar(port=args.port, baud=args.baud)
    if not car.connect():
        logger.error("Could not connect to Arduino. Exiting.")
        sys.exit(1)

    # ── 2. Open camera ───────────────────────────────────────────────────
    cam = VideoStream(
        mode=args.camera,
        device_index=args.device,
        rtsp_url=args.rtsp,
        frame_width=args.width,
        frame_height=args.height,
    )
    if not cam.open():
        logger.error("Could not open camera. Exiting.")
        car.cleanup()
        sys.exit(1)

    # ── 3. Safety monitor and dashboard ──────────────────────────────────
    monitor   = SafetyMonitor(car, cam, warning_seconds=args.warning,
                              confidence=args.confidence)
    dashboard = Dashboard()

    logger.info("Safety Car running.")
    logger.info("Kid controls car with Bluetooth phone app.")
    logger.info("CV monitors for obstacles. Press Q in dashboard to quit.")

    try:
        while True:
            # Grab latest frame
            frame = cam.read()

            # Run detection + state machine
            detections, state, progress = monitor.update(frame)

            # Render dashboard
            key = dashboard.render(
                frame       = frame,
                detections  = detections,
                state       = state,
                bt_command  = car.current_bt_command,
                warning_progress = progress,
            )

            # Q key exits
            if key == ord("q"):
                logger.info("Q pressed — shutting down.")
                break

            # ~30 FPS cap — YOLO is the real bottleneck anyway
            time.sleep(0.005)

    except KeyboardInterrupt:
        logger.info("Ctrl-C — shutting down.")

    finally:
        car.override_resume()   # always lift any active override before exit
        cam.close()
        car.cleanup()
        dashboard.close()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
