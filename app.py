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

# Sign Up Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        # Check if the username already exists (example logic)
        user_exists = mongo.db.users.find_one({'username': username})
        
        if user_exists:
            flash("Username already exists!", 'danger')  # Flash message for duplicate username
            return redirect(url_for('signup'))  # Redirect back to signup page
        
        # Proceed with registration
        hashed_password = generate_password_hash(password)
        mongo.db.users.insert_one({'username': username, 'password': hashed_password, 'email': email})
        
        flash("User registered successfully!", 'success')  # Flash success message
        return redirect(url_for('login'))  # Redirect to login after successful signup

    # If it's a GET request, render the signup form
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

        # Here is where the login check code goes
        if user_found:
            # Check if the password is correct
            if check_password_hash(user_found['password'], password):
                session['username'] = user_found['username']  # Store the username in session
                flash("Login successful!", 'success')  # Flash success message
                return redirect(url_for('home'))  # Redirect to home page after successful login
            else:
                flash("Invalid password! Please try again.", 'danger')  # Incorrect password message
        else:
            flash("User not found! Please check your username or email.", 'danger')  # User not found message

    return render_template('login.html')


# About Us Page Route
@app.route('/about_us')
def about_us():
    # Check if user is logged in
    if 'username' not in session:
        flash("You need to log in to access this page!", 'warning')
        return redirect(url_for('login'))
    return render_template('about_us.html')

# Profile Page Route
@app.route('/profile')
def profile():
    # Check if user is logged in
    if 'username' not in session:
        flash("You need to log in to access this page!", 'warning')
        return redirect(url_for('login'))
    
    username = session['username']
    user = mongo.db.users.find_one({'username': username})
    return render_template('profile.html', user=user)

# Update Password Route
@app.route('/update_password', methods=['GET', 'POST'])
def update_password():
    # Check if user is logged in
    if 'username' not in session:
        flash("You need to log in to access this page!", 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        username = session['username']
        user = mongo.db.users.find_one({'username': username})

        if user and check_password_hash(user['password'], old_password):
            new_hashed_password = generate_password_hash(new_password)
            mongo.db.users.update_one({'username': username}, {'$set': {'password': new_hashed_password}})
            flash("Password updated successfully!", 'success')
            return redirect(url_for('profile'))
        else:
            flash("Old password is incorrect!", 'danger')

    return render_template('update_password.html')

# Logout Route (to clear session data)
@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    flash("You have been logged out successfully!", 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
