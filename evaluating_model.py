import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV


# Please have a look at data_preprocessing.py before reading this

# This function takes the face descriptions extracted from the images by the data_preprocessing() function,
# uses it to train three models and choose the best one for each case by the voting classifier model,
# fine-tunes the parameters by using GridSearchCV
# and saves these parameters in a file called machinelearning_face_person_identity.pickle

# Details about the models have been provided in the readme

def evaluating_model():
    # Load the data saved by data_preprocessing.py which contains face descriptions and labels
    data = pickle.load(open(f'models\\data_face_features.pickle', mode='rb'))

    # Split the data into dependent and independent variables
    x = np.array(data['data'])  # independent variable
    y = np.array(data['label'])  # dependent variable

    # Here x is in 3 dimensions so change it to 2 dimension
    x = x.reshape(-1, 128)

    # Split the data into train and test
    x_train, x_test, y_train, y_test = train_test_split(x, y, train_size=0.8, random_state=0)

    # Load the first model, Logistic Regression
    # The parameters that are tuned for this model are penalty and solver
    model_logistic = LogisticRegression()

    # Train logistic regression
    model_logistic.fit(x_train, y_train)

    # Load the second model, Support Vector Machines
    # The parameters that are tuned for this model are C and gamma
    model_svc = SVC(probability=True)

    # Train SVC
    model_svc.fit(x_train, y_train)

    # Load the third model, Random Forest Classifier
    # The parameters that are tuned for this model are number of estimators and max depth
    model_rf = RandomForestClassifier()

    # Train Random Forest Classifier
    model_rf.fit(x_train, y_train)

    # Load the fourth model, Voting Classifier
    # Pass the above three models along with their labels and weights
    # This model combines the three machine learning models
    model_voting = VotingClassifier(estimators=[
        ('logistic', LogisticRegression()),
        ('svm', SVC(probability=True)),
        ('rf', RandomForestClassifier())
    ], voting='soft', weights=[2, 3, 1])  # Here the weights assigned are 2,3,1 respectively

    # Train Voting Classifier
    model_voting.fit(x_train, y_train)

    # This function tells the accuracy score and f1 score of the model after training
    def get_report(model, x_train, y_train, x_test, y_test):
        # With the x_train data we can obtain y_train results using model.predicts
        y_pred_train = model.predict(x_train)
        y_pred_test = model.predict(x_test)

        # Calculate the train and test accuracy
        acc_train = accuracy_score(y_train, y_pred_train)
        acc_test = accuracy_score(y_test, y_pred_test)

        # Calculate the train and test f1 score
        f1_score_train = f1_score(y_train, y_pred_train, average='macro')
        f1_score_test = f1_score(y_test, y_pred_test, average='macro')

        # Print the accuracy and f1 score
        print('Accuracy Train = %0.2f ' % acc_train)
        print('Accuracy Test = %0.2f ' % acc_test)
        print('f1 Train = %0.2f ' % f1_score_train)
        print('f1 Test = %0.2f ' % f1_score_test)

    # This will print the accuracy and f1 score of the voting classifier
    get_report(model_voting, x_train, y_train, x_test, y_test)

    # Find the tuned parameters using GridSearchCV
    # This is done by passing the parameters that we are tuning and
    # the values we want to check
    # For this project, I have put in list of values instead of range
    # because the training time for range was very long
    model_grid = GridSearchCV(model_voting,
                              param_grid={
                                  'logistic__penalty': ['l1', 'l2'],
                                  'logistic__solver': ['liblinear'],
                                  'svm__C': [3, 5, 7, 10],
                                  'svm__gamma': [0.1, 0.3, 0.5],
                                  'rf__n_estimators': [5, 10, 50],
                                  'rf__max_depth': [3, 5, 7],
                              }, scoring='accuracy', cv=5, n_jobs=-1, verbose=2)

    # Fit the model
    model_grid.fit(x_train, y_train)

    # Get the model with the best estimation and tuned parameters
    model_best_estimator = model_grid.best_estimator_

    # Dump this model into a pickle file
    pickle.dump(model_best_estimator, open(f'models\\machinelearning_face_person_identity.pickle', mode='wb'))
