import os
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Use the real special name __name__
app = Flask(__name__)
# Use an environment variable in production; fallback to a default for dev
app.secret_key = os.environ.get('SECRET_KEY', 'university_secret_key')

# --- 1. DATABASE CONFIGURATION ---
# Connect to Render's Postgres DB or a local file
database_url = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 2. DATABASE MODELS ---
registrations = db.Table('registrations',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    enrollment_no = db.Column(db.String(50), unique=True, nullable=False)
    address = db.Column(db.String(200))
    courses = db.relationship('Course', secondary=registrations, backref='students')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    prof = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    enrolled = db.Column(db.Integer, default=0)

# --- 3. TEMPLATES (unchanged; keep your templates) ---
HTML_TEMPLATE = """ ... (your full HTML_TEMPLATE goes here) ... """
LOGIN_TEMPLATE = """ ... (your LOGIN_TEMPLATE) ... """
SIGNUP_TEMPLATE = """ ... (your SIGNUP_TEMPLATE) ... """
PROFILE_TEMPLATE = """ ... (your PROFILE_TEMPLATE) ... """

# --- 4. HELPERS ---
def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            next_url = request.full_path.rstrip('?')
            return redirect(url_for('login', next=next_url))
        return f(*args, **kwargs)
    return decorated_function

# --- 5. ROUTES ---
@app.route('/')
def home():
    current_user = get_current_user()
    courses = Course.query.order_by(Course.code).all()
    total_credits = sum(c.credits for c in (current_user.courses if current_user else []))
    return render_template_string(HTML_TEMPLATE, courses=courses, current_user=current_user, total_credits=total_credits)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name'].strip()
        enrollment = request.form['enrollment'].strip()
        email = request.form['email'].strip().lower()
        address = request.form['address'].strip()
        password = request.form['password']
        if not (name and enrollment and email and address and password):
            flash("Please fill all fields.", "danger")
            return render_template_string(SIGNUP_TEMPLATE)
        if User.query.filter((User.email == email) | (User.enrollment_no == enrollment)).first():
            flash("Email or Enrollment number already registered.", "warning")
            return redirect(url_for('login'))
        hashed_pw = generate_password_hash(password)
        new_user = User(name=name, email=email, enrollment_no=enrollment, address=address, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
        flash(f"Account created. Welcome, {name}!", "success")
        next_url = request.form.get('next') or request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('home'))
    return render_template_string(SIGNUP_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next') or None
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid credentials.", "danger")
            return render_template_string(LOGIN_TEMPLATE, next=next_url)
        session['user_id'] = user.id
        flash(f"Welcome back, {user.name}!", "success")
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('home'))
    return render_template_string(LOGIN_TEMPLATE, next=next_url)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out.", "info")
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    return render_template_string(PROFILE_TEMPLATE, user=get_current_user())

@app.route('/register/<int:course_id>', methods=['POST'])
@login_required
def register(course_id):
    current_user = get_current_user()
    course = Course.query.get(course_id)
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for('home'))
    if course in current_user.courses:
        flash(f"You are already registered for {course.code}.", "warning")
    elif course.enrolled >= course.capacity:
        flash(f"Sorry, {course.code} is currently full.", "danger")
    else:
        current_user.courses.append(course)
        course.enrolled += 1
        db.session.commit()
        flash(f"Successfully registered for {course.name}!", "success")
    return redirect(url_for('home'))

@app.route('/reset', methods=['POST'])
@login_required
def reset():
    current_user = get_current_user()
    for course in current_user.courses:
        if course.enrolled > 0:
            course.enrolled -= 1
    current_user.courses = []
    db.session.commit()
    flash("Your schedule has been cleared.", "info")
    return redirect(url_for('home'))

# --- 6. INITIALIZATION / SEED ---
def seed_database():
    if Course.query.first() is None:
        initial_courses = [
            Course(code="AM2301", name="Applied Mathematics", prof="Mrs Shrawani Mitkari", credits=4, capacity=30),
            Course(code="CSE2304", name="Data Structures", prof="Mrs Monalisa Hati", credits=3, capacity=50),
            Course(code="FL-301", name="Foreign Language", prof="Mrs Surekha Athawade", credits=4, capacity=40),
            Course(code="DSD2303", name="Digital logic and Computer Architecture", prof="Mrs Saranya Pandian", credits=3, capacity=25),
            Course(code="CSE2302", name="Data Base Management system", prof="Dr Dipak Raskar", credits=2, capacity=60),
            Course(code="CSE2308", name="Java Programming", prof="Dr Deepika Shekhawat", credits=3, capacity=30)
        ]
        db.session.add_all(initial_courses)
        db.session.commit()
        print("Database seeded with your courses!")

# Optional: automatically create DB and seed when the app is imported (useful for Render/gunicorn).
# Control with AUTO_INIT_DB env var; default 'true' so it runs unless you set it to 'false'.
if os.environ.get('AUTO_INIT_DB', 'true').lower() == 'true':
    with app.app_context():
        db.create_all()
        seed_database()

# Keep the usual direct-run guard for local dev
if __name__ == '__main__':
    app.run(debug=True)
