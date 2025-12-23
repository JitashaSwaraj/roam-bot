
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_sitemapper import Sitemapper
import bcrypt
import requests
import datetime
import bard
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request
from deep_translator import GoogleTranslator


# Load the environment variables
load_dotenv()
api_key = os.environ.get("WEATHER_API_KEY")
secret_key = os.environ.get("SECRET_KEY")

# Initialize the app
app = Flask(__name__)
sitemapper = Sitemapper(app=app) # Create and initialize the sitemapper
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
app.secret_key = secret_key

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode(
            'utf8'), bcrypt.gensalt()).decode('utf8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf8'), self.password.encode('utf8'))

with app.app_context():
    db.create_all()

@app.after_request
def add_csp_header(response):
    csp = (
        "default-src 'self'; "
        # Allow external scripts like FontAwesome, Bootstrap, EmailJS, and others
        "script-src 'self' 'unsafe-inline' https://kit.fontawesome.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://emailjs.com; "
        # Allow inline styles and external stylesheets (Bootstrap, FontAwesome, Google Fonts)
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        # Allow fonts from Google Fonts and jsDelivr
        "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        # Allow images from the same origin
        "img-src 'self' data:; "
        # Allow external connections for emailjs and others
        "connect-src 'self' https://emailjs.com; "
        # No frames allowed
        "frame-src 'none'; "
        # Restrict object-src, base-uri, form-action, frame-ancestors, manifest-src, media-src, worker-src
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "manifest-src 'self'; "
        "media-src 'self'; "
        "worker-src 'self'; "
    )
    response.headers['Content-Security-Policy'] = csp
    return response

# Weather Data 
def get_weather_data(api_key: str, city: str, start_date: str, end_date: str) -> dict | None:
    """
    Uses OpenWeather: geocode city -> One Call 3.0 daily forecast.
    start_date/end_date unused for API query (we return daily forecast).
    Returns dict on success or None on failure.
    """
    if not api_key:
        return None
    try:
        # 1) Geocode city -> lat/lon
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}"
        geo_resp = requests.get(geo_url, timeout=10)
        geo_resp.raise_for_status()
        geo = geo_resp.json()
        if not geo:
            return None
        lat = geo[0]["lat"]
        lon = geo[0]["lon"]

        # 2) One Call 3.0 - daily forecast
        weather_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=hourly,minutely,current,alerts&units=metric&appid={api_key}"
        wresp = requests.get(weather_url, timeout=10)
        wresp.raise_for_status()
        return wresp.json()
    except Exception as e:
        # don't crash the app for weather errors
        print("Weather fetch failed:", e)
        return None
    
def generate_itinerary_ai(source, destination, start_date, end_date):
    prompt = f"""
    Create a detailed travel itinerary.

    From: {source}
    Destination: {destination}
    Start Date: {start_date}
    End Date: {end_date}

    Requirements:
    - Day-wise plan
    - Morning / Afternoon / Evening activities
    - Include food suggestions
    - Keep it realistic and concise
    """

    try:
        response = bard.ask(prompt)
        return response.get("content", "AI failed to generate itinerary.")
    except Exception as e:
        print("AI error:", e)
        return "AI itinerary generation failed."


        
@sitemapper.include()  # Include the route in the sitemap
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/planner", methods=["GET", "POST"])
def planner():
    if request.method == "POST":
        session["source"] = request.form["source"]
        session["destination"] = request.form["destination"]
        session["start_date"] = request.form["start_date"]
        session["end_date"] = request.form["end_date"]

        return redirect(url_for("dashboard"))

    return render_template("planner.html")





@sitemapper.include() # Include the route in the sitemap
@app.route("/about")
def about():
    """
    Renders the about.html template.

    Returns:
        The rendered about.html template.
    """
    return render_template("about.html")

@sitemapper.include() # Include the route in the sitemap
@app.route("/contact")
def contact():
    """
    Renders the contact.html template.

    Returns:
        The rendered contact.html template.
    """
    user_email = session.get('user_email', "Enter your email")
    user_name = session.get('user_name', "Enter your name")
    message = ''

    return render_template("contact.html", user_email=user_email, user_name=user_name, message=message)

@sitemapper.include()
@app.route("/translate", methods=["GET", "POST"])
def translate():
    translated_text = ""
    languages = GoogleTranslator().get_supported_languages(as_dict=True)

    if request.method == "POST":
        text = request.form.get("text")
        src_lang = request.form.get("src_lang")
        dest_lang = request.form.get("dest_lang")

        if text and src_lang and dest_lang:
            try:
                translated_text = GoogleTranslator(source=src_lang, target=dest_lang).translate(text)
            except Exception as e:
                flash("Translation failed. Please check the language codes and try again.", "danger")

    return render_template("translate.html", translated_text=translated_text)

@sitemapper.include() # Include the route in the sitemap
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Renders the login.html template.

    Returns:
        The rendered login.html template.
    """
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_email"] = user.email
            flash("Login successful.", "success")
            print(session["user_email"])
            return redirect(url_for("index"))
        
        else:
            flash("Wrong email or password. Please try again or register now.", "danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html")

@sitemapper.include() # Include the route in the sitemap
@app.route("/logout")
def logout():
    """
    Logs the user out.

    Returns:
        Redirects to the login page.
    """
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))

@sitemapper.include() # Include the route in the sitemap
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Renders the register.html template and handles user registration.

    If the request method is GET, the function renders the register.html template.
    If the request method is POST, the function handles user registration by checking if the passwords match,
    checking if the user already exists, and adding the user to the database if they don't exist.

    Returns:
        If the request method is GET, the rendered register.html template.
        If the request method is POST and the user is successfully added to the database, a redirect to the login page.
        If the request method is POST and the passwords don't match or the user already exists, a redirect to the login page with an error message.
    """
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if password == password2:
            # Check if the user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("User already exists. Please log in.", "danger")
                return redirect("/login")
            else:
                user = User(name=name, email=email, password=password)
                db.session.add(user)
                db.session.commit()
                return redirect("/login")
        else:
            flash("Passwords do not match.", "danger")
            return redirect("/register")
    else:
        return render_template("register.html")
    
# Robots.txt
@app.route('/robots.txt')
def robots():
    return render_template('robots.txt')

# Sitemap
@app.route("/sitemap.xml")
def r_sitemap():
    return sitemapper.generate()

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """
    Renders the 404.html template.

    Returns:
        The rendered 404.html template.
    """
    return render_template('404.html'), 404

@app.template_filter('datetimeformat')
def datetimeformat(value):
    import datetime as _dt
    try:
        return _dt.datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d')
    except:
        return value
    

@app.route("/dashboard")
def dashboard():
    try:
        source = session.get("source")
        destination = session.get("destination")
        start_date = session.get("start_date")
        end_date = session.get("end_date")

        # HARD SAFETY CHECK
        if not all([source, destination, start_date, end_date]):
            flash("Please generate itinerary again.", "warning")
            return redirect(url_for("planner"))

        # calculate number of days
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        no_of_day = (end - start).days + 1

        itinerary = bard.generate_itinerary(
            source,
            destination,
            start_date,
            end_date,
            no_of_day
        )

        weather = get_weather_data(
            api_key,
            destination,
            start_date,
            end_date
        )

        return render_template(
            "dashboard.html",
            itinerary=itinerary,
            weather=weather,
            destination=destination
        )

    except Exception as e:
        print("Dashboard Error:", e)
        flash("Something went wrong. Please try again later.", "danger")
        return redirect(url_for("planner"))






# Injecting current time into all templates for copyright year automatically updation
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}

if __name__ == "__main__":
    app.run(debug=True)