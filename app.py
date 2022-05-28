from flask import Flask, render_template, Response, redirect, url_for, flash, session
import cv2
import sqlite3
from pipeline_webcam import pipeline_model
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, Email
from flask_bcrypt import Bcrypt
from datetime import datetime
from pathlib import Path
import time
import Augmentor
import os
from data_preprocessing import data_preprocessing
from evaluating_model import evaluating_model

# ------------------------------------------------
# --------------------SETUP-----------------------
# ------------------------------------------------


# declaring the flask app
app = Flask(__name__)

# setting up SQLAlchemy for database
db = SQLAlchemy(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'

# setting up Bcrypt to encrypt passwords
bcrypt = Bcrypt(app)

# variable to indicate status of attendance
attendance = False

# setting up the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------------------------------------------
# ----------TABLES AND FORMS----------------------
# ------------------------------------------------

# This table stores the user details
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    First_Name = db.Column(db.String(20), nullable=False)
    Last_Name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False)


# This table stores the attendance details
class Attendance(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(20), nullable=False)
    class_name = db.Column(db.String(20), nullable=False)
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)


# FORMS
# This Form takes the registration details
class RegistrationForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20, )], render_kw={"placeholder": "Username"})
    First_Name = StringField(validators=[InputRequired(), Length(min=0, max=20, )],
                             render_kw={"placeholder": "First Name"})
    Last_Name = StringField(validators=[InputRequired(), Length(min=0, max=20, )],
                            render_kw={"placeholder": "Last Name"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20, )],
                             render_kw={"placeholder": "Password"})
    email_id = EmailField(
        validators=[InputRequired(), Length(min=4, max=100, ), Email("This field requires a valid email")],
        render_kw={"placeholder": "Email@example.com"})
    submit = SubmitField("Register")

    # This is a function to check if the username entered is already present in the database
    def validate_username(self, username):
        existing_user_name = User.query.filter_by(username=username.data).first()
        if existing_user_name:
            raise ValidationError("That username already exists. Please choose a different one")


# This form takes the login details
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20, )], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20, )],
                             render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


# ------------------------------------------------
# -----------------FUNCTIONS----------------------
# ------------------------------------------------

# This function identifies the name of the recognized person by using the pipeline model created in pipeline_webcam.py.
# This function returns one value i.e the name of the person
# It is used during attendance marking in the mark_attendance view


def identify(cap):
    # Take the frame from camera
    ret, frame = cap.read()
    # If not taken successfully
    if not ret:
        return None
    # If taken successfully
    # Pass it to the pipeline_model function from the pipeline_webcam.py file
    image, res = pipeline_model(frame)
    # If the face is identified
    if res:
        # Return the face name
        return res['face_name']
    # If the face is not identified return None
    return None


# This is a helper function used in the taking_photos function
# It saves the image in the dataset directory


def saveImage(img, username, imgid):
    # Declare the filename
    filename = f'{imgid}.jpg'

    # Declare the Directory where its stored
    DIR = f'dataset\\{username}'
    # If the directory doesn't exist make it
    Path(DIR).mkdir(parents=True, exist_ok=True)

    # Declare the path where the image has to be saved
    path = f'{DIR}\\{filename}'

    # Write the image to that path
    cv2.imwrite(path, img)


# This function is used to take the photos of the user while registering
# It takes a specified amount of photos and stores it in a directory named after the user
# It takes a 100 photos by default and can be changed by altering the no_of_pics variable
# It is used in the take_photos view

def taking_photos(cap, username):
    # Declare the number of pictures to be taken
    no_of_pics = 100
    count = 1
    # Repeat until count == no_of_pics
    while True:
        # Take a photo from the camera
        ret, frame = cap.read()
        if not ret:
            break
        # Store it using saveImage function
        if count <= no_of_pics:
            saveImage(frame, username, count)
            count += 1
            # Wait for 1 second between photos
            time.sleep(1)
        else:
            break


# This function is used to augment the dataset generated by the taking_photos function
# This is done using the Augmentor python library which picks a photo randomly from the specified directory
# and augments the specified properties like zoom, brightness etc
# This function is used immediately after generating the dataset in the take_photos view

def augment_dataset(DIR):
    # Declare how many augmented images have to be generated
    sample_size = 500
    try:
        # Declare the Directory of the images that are to be augmented
        path = DIR

        # Check if the images have already been augmented
        check = os.path.isdir(f'{path}\\output')

        # If the images have not yet been augmented
        if not check:
            # Augment them according to these properties
            p = Augmentor.Pipeline(path)
            p.zoom(probability=0.3, min_factor=0.8, max_factor=1.5)
            p.flip_random(probability=0.4)
            p.random_brightness(probability=0.3, min_factor=0.3, max_factor=1.2)
            p.skew(probability=0.4, magnitude=0.25)
            p.rotate(probability=0.3, max_left_rotation=0.3, max_right_rotation=0.3)
            p.sample(sample_size)
        else:
            pass
    except:
        pass


# ------------------------------------------------
# -------------------Views------------------------
# ------------------------------------------------

# This is main page of the website
# It contains 2 urls to login and mark_attendance views

@app.route('/')
def index():
    return render_template('index.html')


# ------------------------------------------------
# ----------MAIN PAGE BEGINS----------------------
# ------------------------------------------------


# This is the login view
# This contains a form to take the login information and check whether it matches with the database
# After logging in, the user is directed to their respective dashboards

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Form to take the login information
    form = LoginForm()

    # If the form is valid
    if form.validate_on_submit():
        # Search for the user
        user = User.query.filter_by(username=form.username.data).first()

        # If the user exists
        if user:

            # Decrypt the password present in the database corresponding to the user and compare it
            # If the passwords match
            if bcrypt.check_password_hash(user.password, form.password.data):

                # Login the user
                login_user(user)

                # If the user is an admin
                if user.is_admin:
                    session['username'] = user.username

                    # Redirect to the admin dashboard
                    return redirect(url_for('admin_dashboard'))
                # If the user is not an admin
                else:
                    session['username'] = user.username

                    # Redirect the user to the dashboard
                    return redirect(url_for('dashboard'))
            # If the passwords do not match
            else:
                # Give an error message
                flash('The password entered is incorrect')

        # If the user does not exist
        else:
            # Give an error message
            flash('User Does not Exist', 'error')

    # Render the login template
    return render_template('login.html', form=form)


# This is the view for marking the attendance
# This can be reached by the main page
@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    # Open the camera with port 0
    cap = cv2.VideoCapture(0)

    # Identify the user
    user = identify(cap)[-1]

    # Get the course whose attendance has to be marked
    course = session['course']

    # Store the identified user in a session for other views
    session['username'] = user

    # Release the camera
    cap.release()

    # Retrieve the data whether the user wants to check in or check out
    choice = session['choice']

    # If the user is identified
    if user is not None:
        # Store the username in name
        name = user

        # If the user wants to check in
        if choice == 'check_in':
            # Get the current time
            now = datetime.now()
            # Make a new attendance entry with current time as check in time for the user
            new_attendance = Attendance(username=name, check_in=now, check_out=None, class_name=course)

            # Update the database
            db.session.add(new_attendance)
            db.session.commit()

            # Redirect to the confirmation page
            return redirect(url_for('confirmation'))
        # If the user wants to check out
        elif choice == 'check_out':
            # Get the current time
            now = datetime.now()
            # Search the database for a check in entry by the user for the course
            user = Attendance.query.filter_by(username=name, class_name=course, check_out=None).first()
            # If the user has checked in
            if user is not None:
                # Update the database
                user.check_out = now
                db.session.commit()

                # Redirect to the confirmation page
                return redirect(url_for('confirmation'))
            # If the user has not checked in
            else:
                # Redirect to the error page
                return redirect(url_for('error'))

        # Render the mark attendance template
        return render_template('mark_attendance.html', name=name)
    # If the user is not recognized
    else:

        # Retry by rendering the mark attendance template again
        return render_template('mark_attendance.html', name='None')


# This is the error view
# User is redirected to this if there is an error
@app.route('/error')
def error():
    user = session['username']
    course = session['course']

    # Render the error template
    return render_template('error.html', user=user, course=course)


# This view is for choosing the course for which attendance is to be marked
@app.route('/choose_course')
def choose_course():
    # Render the choose course template
    return render_template('choose_course.html')


# -------------Choice Views-----------------------

# This is cs101 view
@app.route('/cs101')
def cs101():
    # Store the choice in the session
    session['course'] = 'cs101'

    # If attendance has been started
    if attendance:
        # Redirect to the check in or check out choice
        return redirect(url_for('in_or_out'))
    # If the attendance has not been started
    else:
        # Redirect to the attendance not started page
        return redirect(url_for('not_started'))


# This is ma101 view
@app.route('/ma101')
def ma101():
    # Store the choice in the session

    # If attendance has been started
    session['course'] = 'ma101'
    if attendance:
        # Redirect to the check in or check out choice
        return redirect(url_for('in_or_out'))
    else:
        # Redirect to the attendance not started page
        return redirect(url_for('not_started'))


# This is me101 view
@app.route('/me101')
def me101():
    # Store the choice in the session
    session['course'] = 'me101'
    if attendance:
        # Redirect to the check in or check out choice
        return redirect(url_for('in_or_out'))
    else:
        # Redirect to the attendance not started page
        return redirect(url_for('not_started'))


# This is ce101 view
@app.route('/ce101')
def ce101():
    # Store the choice in the session
    session['course'] = 'ce101'
    if attendance:
        # Redirect to the check in or check out choice
        return redirect(url_for('in_or_out'))
    else:
        # Redirect to the attendance not started page
        return redirect(url_for('not_started'))


# This is hs101 view
@app.route('/hs101')
def hs101():
    # Store the choice in the session
    session['course'] = 'hs101'
    if attendance:
        # Redirect to the check in or check out choice
        return redirect(url_for('in_or_out'))
    else:
        # Redirect to the attendance not started page
        return redirect(url_for('not_started'))


# This is cs110 view
@app.route('/cs110')
def cs110():
    # Store the choice in the session
    session['course'] = 'cs110'
    if attendance:
        # Redirect to the check in or check out choice
        return redirect(url_for('in_or_out'))
    else:
        # Redirect to the attendance not started page
        return redirect(url_for('not_started'))


# -------------Choice Views-----------------------

# This is the check in or check out choice view
@app.route('/in_or_out')
def in_or_out():
    # This renders the template for the choice
    return render_template('choice.html')


# This is the check in choice view
@app.route('/check_in')
def check_in():
    # Store the choice in the session
    session['choice'] = 'check_in'
    return redirect(url_for('mark_attendance'))


# This is the check out choice view
@app.route('/check_out')
def check_out():
    # Store the choice in the session
    session['choice'] = 'check_out'
    return redirect(url_for('mark_attendance'))


# This is the confirmation page
@app.route('/confirmation', methods=['GET', 'POST'])
def confirmation():
    # Retrieve the username from the session
    user = session['username']

    # Render the confirmation template
    return render_template('confirmation.html', user=user)


# This is the attendance not started view
@app.route('/not_started')
def not_started():
    # Render the template to tell attendance has not yet been started
    return render_template('not_started.html')


# ------------------------------------------------
# ----------MAIN PAGE ENDS------------------------
# ------------------------------------------------


# This view is for the user dashboard after logging in
# It displays a page with urls to view attendance and logout
@app.route('/dashboard', methods=['GET', 'POST'])
# This can only be accessed if there is a user logged in
@login_required
def dashboard():
    # take the username from the session
    user = session['username']
    # render the dashboard template
    return render_template('dashboard.html', name=user)


# This view is for the admin dashboard after logging in
# It displays a page with urls to manage attendance, register a new user, train the model and logout
@app.route('/admin_dashboard', methods=['GET', 'POST'])
# This can only be accessed if there is a user logged in
@login_required
def admin_dashboard():
    # take the username from the session
    user = session['username']
    # render the admin dashboard template
    return render_template('admin_dashboard.html', name=user)


# This is the view for registering new users
# This can only be accessed by the admin

@app.route('/register', methods=['GET', 'POST'])
# This can only be accessed if there is an admin logged in
@login_required
def register():
    # This is the form to take the registration details
    form = RegistrationForm()

    # This is to take the username from the form and add it to the session
    username = form.username.data
    session['username'] = username

    # This is to check if the form is valid
    check = form.validate_on_submit()

    # If the form is valid
    if check:
        # Search the database for entered email
        email = User.query.filter_by(email=form.email_id.data).first()

        # If the email exists
        if email:
            # Give an error message
            flash("The email ID already exists", 'error')

            # Render the register template
            return render_template('register.html', form=form, check=check)

        # If the email does not exist
        # hash the password before storing the information
        hashed_password = bcrypt.generate_password_hash(form.password.data)

        # Store the details in a variable
        new_user = User(username=form.username.data,
                        First_Name=form.First_Name.data,
                        Last_Name=form.Last_Name.data,
                        email=form.email_id.data,
                        password=hashed_password,
                        is_admin=False)

        # Add it to the database
        db.session.add(new_user)
        db.session.commit()

        # Redirect to generate the dataset for the registered user
        return redirect(url_for('generate_dataset'))

    # If the form is not valid according the validator in RegistrationForm
    else:
        # Give an error
        flash('The Username already Exists', 'error')
        # Render the register template
        return render_template('register.html', form=form, check=check)


# ------------------------------------------------
# ----------ADMIN DASHBOARD BEGINS----------------
# ------------------------------------------------

# This is the view for logging users out
# In order to logout, a user must be logged in
@app.route('/logout', methods=['GET', 'POST'])
# This view can only be accessed if there is a user logged in
@login_required
def logout():
    # Logout the user
    logout_user()

    # After logging out redirect to the main page
    return redirect(url_for('index'))


# This is the view to generate dataset after registering a new user
# This is accessed immediately after registration
@app.route('/generate_dataset', methods=['GET', 'POST'])
# This view can only be accessed if there is an admin logged in
@login_required
def generate_dataset():
    # This is only a waiting page
    # After 2 seconds, it is redirected to take_photos where the photos are actually taken
    return render_template('generate_dataset.html')


# This is where the photos are taken actually
# generate_dataset redirects to this view after 2 seconds
@app.route('/take_photos', methods=['GET', 'POST'])
# This view can only be accessed if there is an admin logged in
@login_required
def take_photos():
    # Open the camera connected to port 0
    cap = cv2.VideoCapture(0)

    # Get the user name from the session
    username = session['username']

    # Call the taking_photos function and pass the camera and the username to it
    taking_photos(cap, username)

    # Declare the directory where the photos are stored
    # Here they are stored in " /dataset/username/ "
    DIR = f'dataset\\{username}'

    # Call the augment_dataset function to augment the dataset generated and pass the Directory
    augment_dataset(DIR)

    # Release the camera
    cap.release()

    # Render the confirmation page after everything is done
    return render_template('take_photos.html')


# This is the view to train the model after registering a new user
# This is a separate view because this process takes time and
# training after registering every single user is not efficient
# This is because you can register multiple users and then train the model
# with all the new users
@app.route('/start_train', methods=['GET', 'POST'])
# This view can only be accessed if there is an admin logged in
@login_required
def start_train():
    # This function is imported from the data_preprocessing.py file
    # This converts the images present in the dataset into vectors that are used to train the model
    # More details are present in the data_preprocessing.py file in the form of comments
    data_preprocessing()

    # This function is imported from the evaluating_model.py file
    # This produces the newly trained model in the form of machinelearning_face_person_identity.pickle in models folder
    # More details are present in the evaluating_model.py file in the form of comments
    evaluating_model()

    # After the above two functions are complete it renders a confirmation page
    # and redirects to the admin_dashboard
    return render_template('start_train.html')


# This is the waiting view
# This is used when the model is being trained as it takes a long time
@app.route('/waiting', methods=['GET', 'POST'])
# This view can only be accessed if there is an admin logged in
@login_required
def waiting():
    # This renders the waiting template
    return render_template('waiting.html')


# This is the view for managing attendance
# This view controls whether attendance is started or not
@app.route('/manage_attendance')
# This view can only be accessed if there is an admin logged in
@login_required
def manage_attendance():
    # This renders a template which gives a choice for starting or stopping attendance
    return render_template('manage_attendance.html')


# This is the view which starts attendance
# This is reached by the manage_attendance view
@app.route('/start_attendance')
# This view can only be accessed if there is an admin logged in
@login_required
def start_attendance():
    # Set the attendance status as started
    global attendance
    attendance = True

    # Render confirmation template and redirect to dashboard
    return render_template('start_attendance.html')


# This is the view which starts attendance
# This is reached by the manage_attendance view
@app.route('/stop_attendance')
# This view can only be accessed if there is an admin logged in
@login_required
def stop_attendance():
    # Set the attendance status as stopped
    global attendance
    attendance = False

    # Render confirmation template and redirect to dashboard
    return render_template('stop_attendance.html')


# ------------------------------------------------
# ----------ADMIN DASHBOARD ENDS------------------
# ------------------------------------------------


# ------------------------------------------------
# ----------USER DASHBOARD BEGINS-----------------
# ------------------------------------------------


# This is the view for viewing the attendance of the logged-in user
# This can be accessed by the user dashboard
# It displays the attendance data according to the course they requested

@app.route('/view_attendance')
# This view can only be accessed if there is a user logged in
@login_required
def view_attendance():
    # Connect to the database
    con = sqlite3.connect("database.db")
    cur = con.cursor()

    # Get the username of the person logged in
    username = current_user.username

    # Get the requested course
    course = session['course']

    # These are the SQL Query for getting the attendance details
    selectsql = "SELECT * FROM attendance where username = " + " '" + username + "' and class_name = " + " '" + course + "' "
    totalsql = "SELECT count(*) FROM attendance where username = " + " '" + username + "' and class_name = " + " '" + course + "' "

    # Execute the SQL Queries mentioned above and store them in variables
    cur.execute(selectsql)
    data = cur.fetchall()  # This contains id, username, class_name, check_in, check_out
    cur.execute(totalsql)
    total = cur.fetchall()  # This contains count of how many classes attended

    # Pass the variables into the template and render it
    return render_template('view_attendance.html', data=data, total=total, course=course)


# This view is for choosing the course for which attendance has to be viewed
@app.route('/choose_view')
# This view can only be accessed if there is a user logged in
@login_required
def choose_view():
    # Render the choose view template
    return render_template('choose_view.html')


# -------------Choice Views-----------------------
# This is the view for cs101 choice
@app.route('/cs101_view')
# This view can only be accessed if there is a user logged in
@login_required
def cs101_view():
    session['course'] = 'cs101'
    return redirect(url_for('view_attendance'))


# This is the view for ma101 choice
@app.route('/ma101_view')
# This view can only be accessed if there is a user logged in
@login_required
def ma101_view():
    session['course'] = 'ma101'
    return redirect(url_for('view_attendance'))


# This is the view for me101 choice
@app.route('/me101_view')
# This view can only be accessed if there is a user logged in
@login_required
def me101_view():
    session['course'] = 'me101'
    return redirect(url_for('view_attendance'))


# This is the view for ce101 choice
@app.route('/ce101_view')
# This view can only be accessed if there is a user logged in
@login_required
def ce101_view():
    session['course'] = 'ce101'
    return redirect(url_for('view_attendance'))


# This is the view for hs101 choice
@app.route('/hs101_view')
# This view can only be accessed if there is a user logged in
@login_required
def hs101_view():
    session['course'] = 'hs101'
    return redirect(url_for('view_attendance'))


# This is the view for cs110 choice
@app.route('/cs110_view')
# This view can only be accessed if there is a user logged in
def cs110_view():
    session['course'] = 'cs110'
    return redirect(url_for('view_attendance'))


# -------------Choice Views-----------------------

# ------------------------------------------------
# ----------USER DASHBOARD ENDS-------------------
# ------------------------------------------------


# For running the flask App
if __name__ == '__main__':
    app.run(debug=True)
