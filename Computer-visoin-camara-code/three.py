# Code 3: Detect Red Color with Mask (Slide 8)

import cv2
import numpy as np


lower_red = np.array([0, 120, 70])
upper_red = np.array([10, 255, 255])
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, lower_red, upper_red)

    cv2.imshow("Red Mask", mask)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()


