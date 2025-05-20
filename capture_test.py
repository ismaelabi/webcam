import cv2

cap = cv2.VideoCapture(0)  # Try 1 or 2 if 0 doesn't work

if not cap.isOpened():
    print("Cannot open camera")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting...")
        break

    cv2.imshow('Webcam Test', frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
