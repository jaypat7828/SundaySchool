# Code 4: Complete Red Detection Program (Full Integration)

import cv2
import numpy as np
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Convert to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define red range
    lower_red = np.array([0, 120, 70])
    upper_red = np.array([10, 255, 255])

    # Create mask
    mask = cv2.inRange(hsv, lower_red, upper_red)

    # Display results
    cv2.imshow("Original", frame)
    cv2.imshow("Red Mask", mask)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
