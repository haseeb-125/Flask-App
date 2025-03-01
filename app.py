from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages


# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/Climate_DB"
mongo = PyMongo(app)

def ClimateData():
    return {
        "temperature": round(random.uniform(15, 35), 2),  # Temperature in °C
        "humidity": random.randint(30, 80),  # Humidity in %
        "air_quality": random.choice(["Good", "Moderate", "Poor", "Unhealthy"]),
        "wind_speed": round(random.uniform(1, 15), 2),  # Wind Speed in km/h
        "forecast": [
            {"day": "Monday", "temp": random.randint(18, 30)},
            {"day": "Tuesday", "temp": random.randint(18, 30)},
            {"day": "Wednesday", "temp": random.randint(18, 30)},
            {"day": "Thursday", "temp": random.randint(18, 30)},
            {"day": "Friday", "temp": random.randint(18, 30)},
        ],
    }

# Home Page Route
@app.route('/')
def home():

    climate_data = ClimateData()
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Retrieve the username from the session for greeting
    username = session['username']
    
    return render_template('home.html', username=username , data=climate_data)

# Sign Up Route

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        gender = request.form.get("gender")

        if not (username and email and password and gender):
            flash("All fields are required!", "danger")
            return redirect(url_for("signup"))

        existing_user = mongo.db.users.find_one({"email": email})
        if existing_user:
            flash("User already exists with this email!", "danger")
            return redirect(url_for("signup"))

        hashed_password = generate_password_hash(password)

        # Save new user to MongoDB
        mongo.db.users.insert_one({
            "username": username,
            "email": email,
            "password": hashed_password,
            "gender": gender
        })

        flash("Account created successfully! You can now login.", "success")
        print("DEBUG: Flash message set - Account created successfully!")  # ✅ Debug log

        return redirect(url_for("login"))

    return render_template("signup.html")


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
    if 'username' not in session:
        flash("You need to log in to access this page!", 'warning')
        return redirect(url_for('login'))
    
    username = session['username']
    user = mongo.db.users.find_one({'username': username})

    if not user:
        flash("User not found!", 'danger')
        return redirect(url_for('login'))

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
