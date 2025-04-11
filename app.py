from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from flask import request, jsonify
import pandas as pd
import plotly.express as px
from flask_cors import CORS
import  re 

app = Flask(__name__)
CORS(app)
app.secret_key = "your_secret_key"

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/Climate_DB"
mongo = PyMongo(app)

# API Configuration
API_KEY = "6746ffcb6b9c2c75f6b942d0180088e3"
API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_live_weather_data(city):
    try:
        params = {
            'q': city,
            'appid': API_KEY,
            'units': 'metric'
        }
        response = requests.get(API_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        return {
            "temperature": data['main']['temp'],
            "humidity": data['main']['humidity'],
            "wind_speed": data['wind']['speed'],
            "air_quality": "Good"  # Placeholder - real air quality would need another API
        }
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None

# Load and clean the climate data
def load_and_clean_data():
    df = pd.read_csv("Cleaned_Environment_Temperature.csv", encoding='latin1')
    df = df.dropna(subset=[col for col in df.columns if col.startswith('Y')])
    df_melted = df.melt(id_vars=['Area', 'Months', 'Element', 'Unit'], 
                       var_name='Year', 
                       value_name='Temperature Change')
    df_melted['Year'] = df_melted['Year'].str.extract(r'(\d+)')
    df_melted['Year'] = df_melted['Year'].fillna(0).astype(int)
    return df_melted

# Add this with your other route definitions
@app.route('/get_weather')
def get_weather():
    city = request.args.get('city')
    if not city:
        return jsonify({"error": "City name is required"}), 400
    
    try:
        api_key = "6746ffcb6b9c2c75f6b942d0180088e3"
        
        # First get the coordinates for the city
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}"
        geo_response = requests.get(geo_url)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        
        if not geo_data:
            return jsonify({"error": "City not found"}), 404
            
        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']
        
        # Get current weather data
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        # Get air quality data
        aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
        aqi_response = requests.get(aqi_url)
        aqi_response.raise_for_status()
        aqi_data = aqi_response.json()
        
        # Map AQI value to quality description
        aqi_map = {
            1: "Good",
            2: "Fair",
            3: "Moderate",
            4: "Poor",
            5: "Very Poor"
        }
        aqi_value = aqi_data['list'][0]['main']['aqi']
        air_quality = aqi_map.get(aqi_value, "Unknown")
        
        return jsonify({
            "temperature": weather_data['main']['temp'],
            "humidity": weather_data['main']['humidity'],
            "wind_speed": weather_data['wind']['speed'],
            "air_quality": air_quality,
            "air_quality_index": aqi_value,
            "city": weather_data['name'],
            "country": weather_data['sys']['country'],
            "coordinates": {
                "latitude": lat,
                "longitude": lon
            }
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API error: {str(e)}"}), 500
    except (KeyError, IndexError) as e:
        return jsonify({"error": f"Unexpected API response format: {str(e)}"}), 500
@app.route('/api/countries')
def get_countries():
    try:
        df = pd.read_csv("Cleaned_Environment_Temperature.csv", encoding='latin1')
        countries = df['Area'].unique().tolist()
        return jsonify(sorted([c for c in countries if pd.notna(c)]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cities/<country>')
def get_cities(country):
    try:
        df = pd.read_csv("Cleaned_Environment_Temperature.csv", encoding='latin1')
        cities = df[df['Area'] == country]['Months'].unique().tolist()
        return jsonify(sorted([c for c in cities if pd.notna(c)]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/climate-data/<country>/<month>')
def get_climate_data(country, month):
    try:
        # Load the CSV data
        df = pd.read_csv("Cleaned_Environment_Temperature.csv", encoding='latin1')
        
        # Clean the month name by removing special characters and normalizing
        month_cleaned = re.sub(r'[^\w\s-]', '', month).strip().lower()
        
        # Get all valid year columns (format Y2000, Y2001, etc.)
        year_cols = [col for col in df.columns if col.startswith('Y') and col[1:].isdigit()]
        
        if not year_cols:
            return jsonify({"error": "No valid year columns found in dataset"}), 500

        # Filter for country and month (case insensitive, partial match)
        filtered = df[
            (df['Area'].str.lower() == country.lower()) & 
            (df['Months'].str.lower().str.contains(month_cleaned))
        ]
        
        if filtered.empty:
            return jsonify({
                "error": f"No data found for {country} and {month}",
                "suggestion": "Try simpler month names like 'Jun' instead of 'Jun-Jul-Aug'"
            }), 404
        
        # Prepare the response data
        years = [int(col[1:]) for col in year_cols]
        temperatures = filtered[year_cols].values[0].tolist()
        
        # Return data in the format expected by the frontend
        return jsonify({
            "x": years,
            "y": temperatures,
            "title": f"Temperature in {country} ({month})",
            "labels": {
                "x": "Year",
                "y": "Temperature (°C)"
            },
            "color": "#4bc0c0",
            "name": "Temperature"
        })
        
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


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

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get live weather data
    default_city = "Pakistan"
    weather_data = get_live_weather_data(default_city)
    
    if not weather_data:
        flash("Could not fetch live weather data", "danger")
        weather_data = {
            "temperature": "N/A",
            "humidity": "N/A",
            "wind_speed": "N/A",
            "air_quality": "N/A",
            "forecast": []  # Empty forecast array to prevent template errors
        }
    else:
        # Add mock forecast data structure if needed by template
        weather_data["forecast"] = []
    
    # Generate forecast labels/temps if template expects them
    forecast_labels = []
    forecast_temps = []
    
    return render_template('home.html', 
                         username=session['username'], 
                         data=weather_data,
                         forecast_labels=forecast_labels,
                         forecast_temps=forecast_temps)
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