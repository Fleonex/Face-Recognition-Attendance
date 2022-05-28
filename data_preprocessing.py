import numpy as np
import cv2
import os
import pickle

# This function performs data preprocessing, i.e. embedding and labelling
# It extracts features from the images using face descriptors and labels each facial feature by its name
# It does this by doing the following steps:
#           Step 1: Detect the face using the face detection model
#           Step 2: Crop the Face and identify the face shape using deep neural networks
#           Step 3: Represent the data in 128 Dimensions which are the facial features of the Face
#           Step 4: Dump the data in a pickle file


def data_preprocessing():
    # Load the models
    # The face detection model used is the res10 caffe model
    face_detection_model = f'models\\res10_300x300_ssd_iter_140000_fp16.caffemodel'
    # This is the proto text for the model
    face_detection_proto = f'models\\deploy.prototxt.txt'
    # The model used for face description is the openface model
    face_descriptor = f'models\\openface.nn4.small2.v1.t7'

    # Read the models
    # As the face detection model is a caffe model, cv2.dnn.readNetFromCaffe has been used
    detector_model = cv2.dnn.readNetFromCaffe(face_detection_proto, face_detection_model)
    # As the face description model is a torch model, cv2.dnn.readNetFromTorch has been used
    descriptor_model = cv2.dnn.readNetFromTorch(face_descriptor)

    # This is a helper function which returns the data about an image in the form of a vector
    def helper(image_path):
        # Open the image from the path and store in a variable
        img = cv2.imread(image_path)

        # Keep a copy of the original image
        image = img.copy()

        # Compute the height and width of the image
        h, w = image.shape[:2]

        # Extract blob from the Image
        # The size has been set to 300x300 as I am using the 300x300 res10 caffe model
        img_blob = cv2.dnn.blobFromImage(image, 1, (300, 300), (104, 177, 123), swapRB=False, crop=False)

        # Set the input for the face detection model as the blob obtained before
        detector_model.setInput(img_blob)

        # Run the model
        # detections will have many possible detections of a face with a confidence score attached to each one
        # It will also contain the co-ordinates of where its detected
        # it is stored in detections[ val1, val2, no_of_detections, i] where i=2 gives confidence score and i=3 to i=6
        # gives the start X, start Y, end X, end Y co-ordinates of the detected face
        detections = detector_model.forward()

        # As there are many detections, the detection with the highest confidence score must be taken
        # If there is at least one face detection
        if len(detections) > 0:
            # Choose the maximum confidence score detection from all the possible detections
            i = np.argmax(detections[0, 0, :, 2])

            # Get the confidence score of the highest confidence score detection
            confidence = detections[0, 0, i, 2]

            # If the confidence is more than 50%
            if confidence > 0.5:
                # Get the co-ordinates of the face which is available in i=3 to i=6 where i is the last parameter
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                # Convert the type to int and input in a tuple
                (startx, starty, endx, endy) = box.astype('int')

                # Take only the detected part of the image i.e. our region of interest
                roi = image[starty:endy, startx:endx].copy()

                # Extract the blob from the region of interest
                faceblob = cv2.dnn.blobFromImage(roi, 1 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=True)

                # Set the input for the face detection model as the blob obtained before
                descriptor_model.setInput(faceblob)

                # Run the model
                # This will perform feature extraction
                # and return a vector containing all the face descriptors and their values
                vectors = descriptor_model.forward()

                # Return the vectors
                return vectors

            # If no face is detected return None
            return None

    # Make a dictionary which holds the data i.e. the face descriptions in the form of vectors
    # and label which tells whose face description it is
    data = dict(data=[], label=[])

    # Go through all the folders in the dataset directory
    folders = os.listdir(f'dataset\\')
    for folder in folders:
        print(folder)
        filenames = os.listdir(f'dataset\\{folder}\\output')
        # Go through all the files in the folders
        for filename in filenames:
            print(filename)
            try:
                path = f'dataset\\{folder}\\output\\{filename}'
                # Get the face description of each image
                vector = helper(path)
                if vector is not None:
                    data['data'].append(vector)
                    data['label'].append(folder)
            except:
                pass

    # Dump the data dictionary into a pickle file
    pickle.dump(data, open(f'models\\data_face_features.pickle', mode='wb'))

    cv2.waitKey(0)

    # Close all the windows
    cv2.destroyAllWindows()
