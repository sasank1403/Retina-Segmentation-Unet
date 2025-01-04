import cv2
import numpy as np
import torch
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from module import build_unet, conv_block, decoder_block, encoder_block
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

app = Flask(__name__)

# Load your trained model
checkpoint_path = "checkpoint.pth"
device = torch.device("cpu")
model = build_unet()  # Assuming build_unet is a function that creates the UNet model
model = torch.load(checkpoint_path, map_location=device)
model.eval()

# Define image processing function
def process_image(image):
    # Preprocess the image
    image = cv2.resize(image, (512, 512))
    x = np.transpose(image, (2, 0, 1)) / 255.0
    x = np.expand_dims(x, axis=0).astype(np.float32)
    x = torch.from_numpy(x)
    x = x.to(device)
    
    # Perform model inference
    with torch.no_grad():
        pred_y = model(x)
        pred_y = torch.sigmoid(pred_y)
        pred_y = pred_y[0].cpu().numpy()
        pred_y = np.squeeze(pred_y, axis=0)
        pred_y = pred_y > 0.5
        pred_y = np.array(pred_y, dtype=np.uint8)
    
    # Convert the segmented image to grayscale
    segmented_image = pred_y * 255

    return segmented_image

@app.route('/', methods=['GET', 'POST'])
def home():
    if 'username' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))
    uploaded_image = None
    segmented_image = None

    if request.method == 'POST':
        # Get the uploaded file from the request
        file = request.files['file']
        
        if file:
            # Read the uploaded image
            img = cv2.imdecode(np.fromstring(file.read(), np.uint8), cv2.IMREAD_COLOR)
            
            # Save the uploaded image temporarily
            uploaded_image_path = "static/uploaded_image.jpg"
            cv2.imwrite(uploaded_image_path, img)

            # Process the image
            segmented_img = process_image(img)
            
            # Save the segmented image temporarily
            segmented_image_path = "static/segmented_image.jpg"
            cv2.imwrite(segmented_image_path, segmented_img)

            uploaded_image = "uploaded_image.jpg"
            segmented_image = "segmented_image.jpg"

    return render_template('index.html', uploaded_image=uploaded_image, segmented_image=segmented_image)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

app.secret_key = '1a2b3c4d5e6d7g8h9i10'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Sathvik@123'   #enter your database password
app.config['MYSQL_DB'] = 'segmentation'

mysql = MySQL(app)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM details WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()

        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for('home'))
        else:
            flash("Incorrect username/password!", "danger")

    return render_template('login.html', title="Login")

@app.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'name' in request.form and 'phone_number' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        phone_number = request.form['phone_number']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM details WHERE username LIKE %s", [username])
        account = cursor.fetchone()

        if account:
            flash("Account already exists!", "danger")
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash("Invalid email address!", "danger")
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash("Username must contain only characters and numbers!", "danger")
        elif not username or not password or not email or not name or not phone_number:
            flash("Please fill out all fields!", "danger")
        else:
            cursor.execute('INSERT INTO details (username, email, password, name, phone_number) VALUES (%s, %s, %s, %s, %s)', (username, email, password, name, phone_number))
            mysql.connection.commit()
            flash("You have successfully registered!", "success")
            return redirect(url_for('login'))

    elif request.method == 'POST':
        flash("Please fill out the form!", "danger")

    return render_template('signup.html', title="Register")

@app.route('/profile',methods=['GET'])
def profile():
    if 'username' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('login'))

    username = session['username']

    # Fetch user details from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM details WHERE username = %s', (username,))
    user = cursor.fetchone()

    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('login'))  # Redirect to login page if user not found

    return render_template('profile.html', user=user)

@app.route('/profile',methods=['POST'])
def profile_update():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        mobile = request.form['mobile']

        username = session['username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE details SET email = %s, name = %s, phone_number = %s WHERE username = %s', (email,name,mobile,username,))
        mysql.connection.commit()  # Commit the transaction
        cursor.close()  # Close the cursor
        return 'Data updated successfully'


if __name__ == '__main__':
    app.run(debug=True)
