from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret key for session management (make sure to change it in production)
app.secret_key = 'your_secret_key'

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/Flask"
mongo = PyMongo(app)

# Home Page Route
@app.route('/')
def home():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Retrieve the username from the session for greeting
    username = session['username']
    
    return render_template('home.html', username=username)

# Signup Page Route  
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        gender = request.form['gender']
        
        # Check if the username or email already exists in MongoDB
        user_by_username = mongo.db.users.find_one({'username': username})
        user_by_email = mongo.db.users.find_one({'email': email})
        
        if user_by_username or user_by_email:
            flash("User with this username or email already exists!", 'danger')
            return redirect(url_for('signup'))  # Redirect to signup page to show the error
        
        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Add new user to MongoDB
        mongo.db.users.insert_one({
            'username': username,
            'password': hashed_password,
            'email': email,
            'gender': gender
        })

        flash("User registered successfully!", 'success')  # Show success message
        return redirect(url_for('login'))  # Redirect to login page after successful signup
    
    return render_template('signup.html')


# Login Page Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username_or_email']  # Username or Email input
        password = request.form['password']
        
        user_found = None

        # Check if the identifier is an email or a username
        if '@' in identifier:  # It's an email
            user_found = mongo.db.users.find_one({'email': identifier})
        else:  # It's a username
            user_found = mongo.db.users.find_one({'username': identifier})

        if user_found and check_password_hash(user_found['password'], password):
            session['username'] = user_found['username']  # Store the username in session
            return redirect(url_for('home'))
        else:
            return "Invalid credentials!"  # Error message if credentials don't match

    return render_template('login.html')


# About Us Page Route
@app.route('/about_us')
def about_us():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('about_us.html')

# Logout Route (to clear session data)
@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
