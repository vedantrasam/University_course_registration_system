import os
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(_name_)
app.secret_key = 'university_secret_key'

# --- 1. DATABASE CONFIGURATION ---
# Connect to Render's Postgres DB or a local file
database_url = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 2. DATABASE MODELS ---

# A "Link" table to remember which user registered for which course
registrations = db.Table('registrations',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    enrollment_no = db.Column(db.String(50), unique=True, nullable=False) # Renamed to avoid confusion with 'enrolled' count
    address = db.Column(db.String(200))
    
    # Relationship: A user can have many courses
    courses = db.relationship('Course', secondary=registrations, backref='students')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    prof = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    enrolled = db.Column(db.Integer, default=0)

# --- 3. TEMPLATES (Updated for DB objects) ---
# I've updated the templates to use 'user.name' instead of dictionary lookups

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>UniReg | Course Registration</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f8f9fa; }
    .navbar { background-color: #2c3e50; }
    .card { border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s; }
    .card:hover { transform: translateY(-5px); }
    .status-full { color: #dc3545; font-weight: bold; }
    .status-open { color: #198754; font-weight: bold; }
    .btn-register { width: 100%; }
  </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark mb-4">
  <div class="container">
    <a class="navbar-brand" href="/">🏛 University Portal</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        {% if current_user %}
          <li class="nav-item me-3"><span class="navbar-text text-white">Student: <strong>{{ current_user.name }}</strong></span></li>
          <li class="nav-item me-2"><a class="btn btn-sm btn-outline-light" href="{{ url_for('profile') }}">Profile</a></li>
          <li class="nav-item"><a class="btn btn-sm btn-outline-light" href="{{ url_for('logout') }}">Logout</a></li>
        {% else %}
          <li class="nav-item"><a class="btn btn-sm btn-outline-light me-2" href="{{ url_for('login', next=request.path) }}">Login</a></li>
          <li class="nav-item"><a class="btn btn-sm btn-light" href="{{ url_for('signup', next=request.path) }}">Sign Up</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>

<div class="container">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
          {{ message }}
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <div class="row">
    <div class="col-md-8">
      <h3 class="mb-3">🎓 Available Courses</h3>
      <div class="row">
        {% for course in courses %}
          <div class="col-md-6 mb-4">
            <div class="card h-100">
              <div class="card-body">
                <h5 class="card-title">{{ course.code }}: {{ course.name }}</h5>
                <h6 class="card-subtitle mb-2 text-muted">{{ course.prof }}</h6>
                <p class="card-text"><strong>Credits:</strong> {{ course.credits }}<br>
                <strong>Status:</strong>
                <span class="{{ 'status-full' if course.enrolled >= course.capacity else 'status-open' }}">
                  {{ course.enrolled }} / {{ course.capacity }} Seats
                </span></p>
              </div>
              <div class="card-footer bg-white">
                {% if current_user %}
                  {% if course in current_user.courses %}
                    <button class="btn btn-secondary btn-register" disabled>Enrolled ✅</button>
                  {% elif course.enrolled >= course.capacity %}
                    <button class="btn btn-outline-danger btn-register" disabled>Class Full 🚫</button>
                  {% else %}
                    <form action="{{ url_for('register', course_id=course.id) }}" method="POST">
                      <button type="submit" class="btn btn-primary btn-register">Register Now</button>
                    </form>
                  {% endif %}
                {% else %}
                  <a href="{{ url_for('login', next=request.path) }}" class="btn btn-outline-primary btn-register">Login to Register</a>
                {% endif %}
              </div>
            </div>
          </div>
        {% endfor %}
      </div>
    </div>

    <div class="col-md-4">
      <div class="card p-3">
        <h4 class="mb-3">📅 My Schedule</h4>
        {% if current_user %}
          {% if current_user.courses %}
            <ul class="list-group list-group-flush">
              {% for course in current_user.courses %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                  <div><strong>{{ course.code }}</strong><br><small>{{ course.name }}</small></div>
                  <span class="badge bg-primary rounded-pill">{{ course.credits }} Cr</span>
                </li>
              {% endfor %}
            </ul>
            <div class="mt-3 pt-3 border-top"><h5>Total Credits: {{ total_credits }}</h5></div>
          {% else %}
            <div class="alert alert-info">You haven't registered for any classes yet.</div>
          {% endif %}
          <div class="mt-4">
            <form action="{{ url_for('reset') }}" method="POST">
              <button class="btn btn-outline-secondary btn-sm w-100">Reset Schedule</button>
            </form>
          </div>
        {% else %}
          <div class="alert alert-warning">Please log in to see and manage your schedule.</div>
        {% endif %}
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<div class="container" style="max-width:520px;margin-top:40px;">
  <h3>Login</h3>
  <form method="POST">
    <input type="hidden" name="next" value="{{ next or '' }}">
    <div class="mb-3"><label>Email</label><input name="email" required class="form-control" type="email"></div>
    <div class="mb-3"><label>Password</label><input name="password" required class="form-control" type="password"></div>
    <button class="btn btn-primary">Login</button>
    <a class="btn btn-link" href="{{ url_for('signup', next=next) }}">Create account</a>
  </form>
</div>
"""

SIGNUP_TEMPLATE = """
<!doctype html>
<title>Sign Up</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<div class="container" style="max-width:600px;margin-top:24px;">
  <h3>Create Account</h3>
  <form method="POST">
    <input type="hidden" name="next" value="{{ request.args.get('next','') }}">
    <div class="row">
      <div class="mb-3 col-md-6"><label>Name</label><input name="name" required class="form-control"></div>
      <div class="mb-3 col-md-6"><label>Enrollment No.</label><input name="enrollment" required class="form-control"></div>
    </div>
    <div class="mb-3"><label>Email</label><input name="email" required class="form-control" type="email"></div>
    <div class="mb-3"><label>Address</label><input name="address" required class="form-control" type="text"></div>
    <div class="mb-3"><label>Password</label><input name="password" required class="form-control" type="password"></div>
    <button class="btn btn-success">Sign Up</button>
    <a class="btn btn-link" href="{{ url_for('login', next=request.args.get('next','')) }}">Already have an account?</a>
  </form>
</div>
"""

PROFILE_TEMPLATE = """
<!doctype html>
<title>Profile</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<div class="container" style="max-width:700px;margin-top:24px;">
  <h3>My Profile</h3>
  <div class="card p-3">
    <p><strong>Name:</strong> {{ user.name }}</p>
    <p><strong>Email:</strong> {{ user.email }}</p>
    <p><strong>Enrollment No.:</strong> {{ user.enrollment_no }}</p>
    <p><strong>Address:</strong> {{ user.address }}</p>
    <a class="btn btn-secondary" href="{{ url_for('home') }}">Back to Home</a>
  </div>
</div>
"""

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

# --- 5. ROUTES (Logic Updated for DB) ---

@app.route('/')
def home():
    current_user = get_current_user()
    courses = Course.query.order_by(Course.code).all()
    
    total_credits = 0
    if current_user:
        total_credits = sum(c.credits for c in current_user.courses)
        
    return render_template_string(
        HTML_TEMPLATE,
        courses=courses,
        current_user=current_user,
        total_credits=total_credits
    )

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
            
        # Check if user exists in DB
        if User.query.filter((User.email == email) | (User.enrollment_no == enrollment)).first():
            flash("Email or Enrollment number already registered.", "warning")
            return redirect(url_for('login'))

        # Create new user in DB
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
        # DB Logic: Link user to course
        current_user.courses.append(course)
        course.enrolled += 1
        db.session.commit()
        flash(f"Successfully registered for {course.name}!", "success")
        
    return redirect(url_for('home'))

@app.route('/reset', methods=['POST'])
@login_required
def reset():
    current_user = get_current_user()
    
    # Decrease enrollment count for all courses the user is in
    for course in current_user.courses:
        if course.enrolled > 0:
            course.enrolled -= 1
            
    # Clear the relationship
    current_user.courses = []
    db.session.commit()
    
    flash("Your schedule has been cleared.", "info")
    return redirect(url_for('home'))

# --- 6. INITIALIZATION ---
def seed_database():
    """Populate database with your specific courses if empty"""
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

if _name_ == '_main_':
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(debug=True)
