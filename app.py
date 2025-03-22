from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import random
import pandas as pd
import plotly.express as px
import plotly.io as pio
from flask_cors import CORS

app = Flask(__name__)  # Define the Flask app first
CORS(app)  # Then initialize CORS
app.secret_key = "your_secret_key"  # Required for flash messages

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/Climate_DB"
mongo = PyMongo(app)

# Function to generate random climate data
def ClimateData():
    return {
        "temperature": round(random.uniform(15, 35)),  # Random temperature between 15°C and 35°C
        "humidity": random.randint(30, 80),  # Random humidity between 30% and 80%
        "wind_speed": round(random.uniform(1, 15)),  # Random wind speed between 1 km/h and 15 km/h
        "air_quality": random.choice(["Good", "Moderate", "Poor", "Unhealthy"]),  # Random air quality
        "forecast": [
            {"day": "Monday", "temp": random.randint(18, 30)},
            {"day": "Tuesday", "temp": random.randint(18, 30)},
            {"day": "Wednesday", "temp": random.randint(18, 30)},
            {"day": "Thursday", "temp": random.randint(18, 30)},
            {"day": "Friday", "temp": random.randint(18, 30)},
        ]
    }

# Load and clean the climate data
def load_and_clean_data():
    # Load the CSV file
    df = pd.read_csv("Cleaned_Environment_Temperature.csv", encoding='latin1')

    # Drop rows with missing temperature change data
    df = df.dropna(subset=[col for col in df.columns if col.startswith('Y')])

    # Melt the dataframe to have a long format for easier plotting
    df_melted = df.melt(id_vars=['Area', 'Months', 'Element', 'Unit'], 
                        var_name='Year', 
                        value_name='Temperature Change')

    # Extract the year from the 'Year' column, handle NaN values, and convert to integer
    df_melted['Year'] = df_melted['Year'].str.extract(r'(\d+)')  # Extract only digits
    df_melted['Year'] = df_melted['Year'].fillna(0).astype(int)  # Fill NaN and convert to int
    df_melted = df_melted.dropna(subset=['Year'])  # Drop remaining NaN rows in 'Year'
    df_melted['Year'] = df_melted['Year'].astype(int)  # Ensure 'Year' is integer

    return df_melted

@app.route('/plot')
def plot():
    # Load or process data
    df_melted = load_and_clean_data()  # Fix: Use the correct function

    # Get countries from the URL query parameter
    countries = request.args.get('countries')  # Example: "USA,India,Canada"

    if countries:
        country_list = countries.split(",")  # Convert string to list
        df_melted = df_melted[df_melted['Area'].isin(country_list)]  # Filter data

    # Create the plot
    fig = px.line(df_melted, x="Year", y="Temperature Change", color="Area")

    return fig.to_html()

# Home Page Route
@app.route('/')
def home():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Retrieve the username from the session for greeting
    username = session['username']
    
    # Load climate data
    climate_data = ClimateData()
    
    # Extract forecast labels and temperatures
    forecast_labels = [item['day'] for item in climate_data['forecast']]
    forecast_temps = [item['temp'] for item in climate_data['forecast']]
    
    return render_template('home.html', username=username, data=climate_data, forecast_labels=forecast_labels, forecast_temps=forecast_temps)

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

# Climate Data Visualization Route
@app.route('/climate_data')
def climate_data():
    # Check if user is logged in
    if 'username' not in session:
        flash("You need to log in to access this page!", 'warning')
        return redirect(url_for('login'))
    
    # Load and clean the data
    df = load_and_clean_data()

    # Filter data for a specific country (e.g., Afghanistan)
    country_data = df[df['Area'] == 'Afghanistan']

    # Create a line chart for temperature change over time
    fig = px.line(country_data, 
                  x='Year', 
                  y='Temperature Change', 
                  color='Months', 
                  title='Temperature Change in Afghanistan Over Time',
                  labels={'Temperature Change': 'Temperature Change (°C)', 'Year': 'Year'})

    # Convert the plot to HTML
    graph_html = pio.to_html(fig, full_html=False)

    # Render the template with the graph and a link to the country route
    return render_template('climate_data.html', graph_html=graph_html, country_name='Afghanistan')

# Country Route
@app.route('/country/<country_name>')
def country(country_name):
    try:
        # Check if user is logged in
        if 'username' not in session:
            return jsonify({"error": "You need to log in to access this page!"}), 401

        # Load and clean the data
        df = load_and_clean_data()

        # Filter data for the selected country (case-insensitive)
        country_data = df[df['Area'].str.lower() == country_name.lower()]

        if country_data.empty:
            # Return a JSON response if the country doesn't exist
            return jsonify({"error": f"No data available for {country_name}. Please select a valid country."}), 404

        # Prepare data for the chart
        chart_data = {
            "x": country_data['Year'].tolist(),  # X-axis data (years)
            "y": country_data['Temperature Change'].tolist(),  # Y-axis data (temperature change)
            "color": country_data['Months'].tolist(),  # Color data (months)
            "title": f"Temperature Change in {country_name} Over Time",
            "labels": {
                "x": "Year",
                "y": "Temperature Change (°C)"
            }
        }

        # Return JSON response with the chart data
        return jsonify({
            "country_name": country_name,
            "chart_data": chart_data
        })
    except Exception as e:
        # Log the error and return a JSON response
        print(f"Error in /country/<country_name> route: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again."}), 500
        

if __name__ == '__main__':
    app.run(debug=True)