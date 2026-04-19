# Code 5: Detect and Draw Bounding Box (Bonus for 7th-8th Graders)
# Objective: Find red objects and draw a box around them
# Difficulty: Advanced

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

    # Find contours (outlines of red objects)
    contours, _ = cv2.findContours(mask, 
        cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Draw box around each red object
    for c in contours:
        if cv2.contourArea(c) > 1500:  # Only large objects
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), 
                (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, "Red!", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, (0, 0, 255), 2)

    cv2.imshow("Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

