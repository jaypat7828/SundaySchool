"""
=============================================================================
ArduinoCar — USB serial bridge to the Arduino
=============================================================================
Two jobs:
  1. READ  — background thread parses "BT:X" lines echoed by Arduino,
             so Python always knows what direction the kid is pressing.
  2. WRITE — override_stop() / override_resume() send 'X' / 'Z' to
             Arduino to engage or lift the Python safety lock.

All original movement methods kept so manual/keyboard mode still works.
=============================================================================
"""

import serial
import serial.tools.list_ports
import threading
import time
import logging

logger = logging.getLogger(__name__)

FORWARD_COMMANDS = {"F", "G", "I"}   # commands that point the camera forward


class ArduinoCar:

    def __init__(self, port: str = None, baud: int = 9600):
        self.port = port or self._auto_detect_port()
        self.baud = baud
        self.serial_conn = None

        self.current_state = "stop"

        # Latest Bluetooth command echoed from Arduino ("BT:F" → "F")
        # Protected by a lock because the reader thread writes it while
        # the main thread reads it.
        self._bt_command = "S"
        self._bt_lock = threading.Lock()

        self._running = False
        self._reader_thread = None

    # ------------------------------------------------------------------
    # Property — thread-safe read of latest BT command
    # ------------------------------------------------------------------

    @property
    def current_bt_command(self) -> str:
        with self._bt_lock:
            return self._bt_command

    def is_forward_command(self) -> bool:
        """True when the kid is pressing a forward-facing direction."""
        return self.current_bt_command in FORWARD_COMMANDS

    # ------------------------------------------------------------------
    # Port auto-detection
    # ------------------------------------------------------------------

    @staticmethod
    def _auto_detect_port() -> str:
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            desc = (p.description or "").lower()
            if any(kw in desc for kw in ("arduino", "ch340", "ch341", "ttyacm")):
                logger.info("Auto-detected Arduino on %s (%s)", p.device, p.description)
                return p.device
        if ports:
            logger.warning("No Arduino found. Available ports:")
            for p in ports:
                logger.warning("  %s — %s", p.device, p.description)
        import sys
        return "COM3" if sys.platform == "win32" else \
               "/dev/cu.usbmodem14101" if sys.platform == "darwin" else \
               "/dev/ttyUSB0"

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """
        Open USB serial and wait for Arduino's "READY" signal.
        Arduino resets when serial opens — "READY" means it has booted
        and is safe to receive commands.
        """
        try:
            self.serial_conn = serial.Serial(
                self.port, self.baud, timeout=1
            )
            logger.info("Serial opened on %s @ %d baud. Waiting for Arduino...", 
                        self.port, self.baud)

            # Start reader thread immediately so we catch "READY"
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._reader_loop, daemon=True
            )
            self._reader_thread.start()

            # Wait up to 5 s for Arduino to boot and send READY
            deadline = time.time() + 5.0
            while time.time() < deadline:
                if self._arduino_ready:
                    logger.info("Arduino ready.")
                    return True
                time.sleep(0.05)

            logger.warning("Arduino did not send READY within 5 s — continuing anyway.")
            return True

        except serial.SerialException as exc:
            logger.error("Serial connection failed: %s", exc)
            logger.error(
                "Tips:\n"
                "  • Check USB cable is plugged in\n"
                "  • Close Arduino IDE Serial Monitor if open\n"
                "  • Linux: sudo usermod -aG dialout $USER\n"
                "  • Specify port manually: --port COM3 or --port /dev/ttyUSB0"
            )
            return False

    # ------------------------------------------------------------------
    # Background reader — parses Arduino serial output
    # ------------------------------------------------------------------

    def _reader_loop(self):
        """
        Reads lines from Arduino continuously.

        Line formats from the sketch:
          "READY"        → Arduino has booted
          "BT:F"         → kid pressed Forward on phone
          "OVERRIDE_ON"  → Arduino confirmed our stop command
          "OVERRIDE_OFF" → Arduino confirmed our resume command
        """
        self._arduino_ready = False

        while self._running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    raw = self.serial_conn.readline()
                    line = raw.decode("utf-8", errors="ignore").strip()

                    if line == "READY":
                        self._arduino_ready = True
                        logger.info("Arduino: READY")

                    elif line.startswith("BT:") and len(line) == 4:
                        # e.g. "BT:F" → store 'F' as current BT command
                        cmd = line[3]
                        with self._bt_lock:
                            self._bt_command = cmd
                        logger.debug("BT command: %s", cmd)

                    elif line in ("OVERRIDE_ON", "OVERRIDE_OFF"):
                        logger.info("Arduino: %s", line)

                else:
                    time.sleep(0.005)

            except (serial.SerialException, OSError):
                # Serial disconnected — stop the thread
                logger.warning("Serial read error — connection lost.")
                break

    # ------------------------------------------------------------------
    # Safety override — these are the key new methods
    # ------------------------------------------------------------------

    def override_stop(self):
        """
        Tell Arduino to stop motors and ignore Bluetooth until resume.
        Python is taking control — safety lock engaged.
        """
        self._send("X")
        self.current_state = "override_stopped"
        logger.info("Safety override: STOP sent to Arduino")

    def override_resume(self):
        """
        Lift the safety lock — Arduino resumes Bluetooth control.
        Arduino will re-execute the last Bluetooth command.
        """
        self._send("Z")
        self.current_state = "resumed"
        logger.info("Safety override: RESUME sent to Arduino")

    # ------------------------------------------------------------------
    # Internal send
    # ------------------------------------------------------------------

    def _send(self, char: str):
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.warning("Serial not open — '%s' dropped.", char)
            return
        try:
            self.serial_conn.write(char.encode("ascii"))
        except serial.SerialException as exc:
            logger.error("Serial write failed: %s", exc)

    # ------------------------------------------------------------------
    # Direct motor commands (used by manual/keyboard mode)
    # ------------------------------------------------------------------

    def forward(self):       self._send("F"); self.current_state = "forward"
    def backward(self):      self._send("B"); self.current_state = "backward"
    def turn_left(self):     self._send("L"); self.current_state = "turn_left"
    def turn_right(self):    self._send("R"); self.current_state = "turn_right"
    def forward_left(self):  self._send("G"); self.current_state = "forward_left"
    def forward_right(self): self._send("I"); self.current_state = "forward_right"
    def back_left(self):     self._send("H"); self.current_state = "back_left"
    def back_right(self):    self._send("J"); self.current_state = "back_right"
    def stop(self):          self._send("S"); self.current_state = "stop"
    def led_on(self):        self._send("W")
    def led_off(self):       self._send("w")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self):
        self.stop()
        self._running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=2.0)
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Serial port closed.")
