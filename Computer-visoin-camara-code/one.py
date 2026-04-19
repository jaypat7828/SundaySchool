# Code 1: Open the Webcam (Starter Code)

# https://github.com/jaypat7828

# pip install opencv-python
# pip3 install opencv-python



import cv2
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("Webcam", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
