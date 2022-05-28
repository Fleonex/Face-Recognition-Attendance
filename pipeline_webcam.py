import numpy as np
import cv2
import pickle

# Please go through evaluating.model.py before this
# All the machine learning models and deep learning models are combined here

# This function takes an image and does the face detection and recognition
def pipeline_model(img):
    # Load the face detection model
    face_detector_model = cv2.dnn.readNetFromCaffe('models\\deploy.prototxt.txt',
                                                   'models\\res10_300x300_ssd_iter_140000_fp16.caffemodel')
    # Load the feature extraction model
    face_feature_model = cv2.dnn.readNetFromTorch('models\\openface.nn4.small2.v1.t7')

    # Load the face recognition model obtained from evaluating_model()
    face_recognition_model = pickle.load(open('models\\machinelearning_face_person_identity.pickle',
                                              mode='rb'))

    # Make a copy of the original image
    image = img.copy()

    # Get the height and width of the image
    h, w = img.shape[:2]

    # Extract the blob from the image
    img_blob = cv2.dnn.blobFromImage(img, 1, (300, 300), (104, 177, 123), swapRB=False, crop=False)

    # Set the input for face detector as the blob obtained before
    face_detector_model.setInput(img_blob)

    # Run the face detection
    detections = face_detector_model.forward()

    # Making a dictionary called machine_learning results to store the
    # confidence score for face detection and recognition, name of the person and number of faces detected

    machinlearning_results = dict(face_detect_score=[],
                                  face_name=[],
                                  face_name_score=[],
                                  count=[])
    try:

        count = 1

        # If at least 1 face is detected in the image
        if len(detections) > 0:
            # for all face detections
            for i, confidence in enumerate(detections[0, 0, :, 2]):
                # if the confidence score is more than 0.5
                if confidence > 0.5:
                    # Get the co-ordinates of the face which is available in i=3 to i=6 where i is the last parameter
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    # Convert the type to int and input in a tuple
                    (startx, starty, endx, endy) = box.astype(int)

                    # Make a rectangle on the obtained face co-ordinates
                    cv2.rectangle(image, (startx, starty), (endx, endy), (0, 255, 0))

                    # Get the region of interest that lies in the face co-ordinates obtained before
                    face_roi = img[starty:endy, startx:endx]

                    # Extract the blob from the region of interest
                    face_blob = cv2.dnn.blobFromImage(face_roi, 1 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False)

                    # Set the input of the feature extraction model as the blob
                    face_feature_model.setInput(face_blob)

                    # Run the model and store the data in a variable
                    vectors = face_feature_model.forward()

                    # Get the predicted face name from the face recognition model
                    # by inputting the features obtained before
                    face_name = face_recognition_model.predict(vectors)[0]

                    # Get the confidence score of the prediction
                    face_score = face_recognition_model.predict_proba(vectors).max()

                    # Insert the name on the image
                    text_face = '{} : {:.0f} %'.format(face_name, 100 * face_score)
                    cv2.putText(image, text_face, (startx, starty), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 2)

                    # Gather the machine learning results in the dictionary
                    machinlearning_results['count'].append(count)
                    machinlearning_results['face_detect_score'].append("{:.0f}%".format(confidence * 100))
                    machinlearning_results['face_name'].append(face_name)
                    machinlearning_results['face_name_score'].append("{:.0f}%".format(face_score * 100))

                    # Increment the count variable
                    count += 1
    except:
        pass

    # return the image with the face detected and the machine learning results
    return image, machinlearning_results

