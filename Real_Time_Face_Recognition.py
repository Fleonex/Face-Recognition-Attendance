import cv2
from pipeline_webcam import pipeline_model

# This is just a demo python code to demonstrate the model created
# This will open a window and recognize your face in real time if your dataset has already been generated

# Open the camera
cap = cv2.VideoCapture(0)

while True:
    # Get the frame from the camera
    ret, frame = cap.read()
    if not ret:
        break
    # Run the pipeline model and get the machine learning resutls
    image, res = pipeline_model(frame)

    # Show the image with the face recognized
    cv2.imshow('face recognition', image)
    if cv2.waitKey(1) == 27:
        break

# Release the camera
cap.release()

# Close all windows
cv2.destroyAllWindows()
