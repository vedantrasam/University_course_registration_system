# app.py
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'university_secret_key'  # for session & flash (demo only)

# --- In-memory user store (demo) ---
# users[email] = {
#   "name": str,
#   "password_hash": str,
#   "enrollment": str,
#   "address": str,
#   "schedule": [course_id, ...]
# }
users = {}

# --- Mock courses ---
courses = [
    {"id": 101, "code": "AM2301", "name": "Applied Mathematics", "prof": "Mrs Shrawani Mitkari", "credits": 4, "capacity": 30, "enrolled": 0},
    {"id": 102, "code": "CSE2304", "name": "Data Structures", "prof": "Mrs Monalisa Hati", "credits": 3, "capacity": 50, "enrolled": 0},
    {"id": 103, "code": "FL-301", "name": "Foreign Language", "prof": "Mrs Surekha Athawade", "credits": 4, "capacity": 40, "enrolled": 0},
    {"id": 104, "code": "DSD2303", "name": "Digital logic and Computer Architecture", "prof": "Mrs Saranya Pandian", "credits": 3, "capacity": 25, "enrolled": 0},
    {"id": 105, "code": "CSE2302", "name": "Data Base Management system", "prof": "Dr Dipak Raskar", "credits": 2, "capacity": 60, "enrolled": 0},
    {"id": 106, "code": "CSE2308", "name": "Java Programming", "prof": "Dr Deepika Shekhawat", "credits": 3, "capacity": 30, "enrolled": 0}
]

# --- Templates (inline) ---
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
    <a class="navbar-brand" href="/">🏛️ University Portal</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        {% if current_user %}
          <li class="nav-item me-3"><span class="navbar-text text-white">Student: <strong>{{ current_user_name }}</strong></span></li>
          <li class="nav-item me-2"><a class="btn btn-sm btn-outline-light" href="{{ url_for('profile') }}">Profile</a></li>
          <li class="nav-item"><a class="btn btn-sm btn-outline-light" href="{{ url_for('logout') }}">Logout</a></li>
        {% else %}
          <!-- send next param so after login user returns to current page -->
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
                  {% if course.id in user_schedule %}
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
          {% if my_schedule_details %}
            <ul class="list-group list-group-flush">
              {% for item in my_schedule_details %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                  <div><strong>{{ item.code }}</strong><br><small>{{ item.name }}</small></div>
                  <span class="badge bg-primary rounded-pill">{{ item.credits }} Cr</span>
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
    <p><strong>Email:</strong> {{ user_email }}</p>
    <p><strong>Enrollment No.:</strong> {{ user.enrollment }}</p>
    <p><strong>Address:</strong> {{ user.address }}</p>
    <a class="btn btn-secondary" href="{{ url_for('home') }}">Back to Home</a>
  </div>
</div>
"""

# --- Helpers ---
def get_current_user_email():
    return session.get('user')

def get_user_schedule(email):
    user = users.get(email)
    return user.get('schedule', []) if user else []

def find_user_by_enrollment(enrollment_no):
    for e, u in users.items():
        if u.get('enrollment') == enrollment_no:
            return e
    return None

# login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user_email():
            next_url = request.full_path.rstrip('?')
            return redirect(url_for('login', next=next_url))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def home():
    current_user = get_current_user_email()
    user_schedule = get_user_schedule(current_user) if current_user else []
    my_schedule_details = [c for c in courses if c['id'] in user_schedule]
    total_credits = sum(c['credits'] for c in my_schedule_details)
    return render_template_string(
        HTML_TEMPLATE,
        courses=courses,
        current_user=current_user,
        current_user_name=(users[current_user]['name'] if current_user and current_user in users else None),
        user_schedule=user_schedule,
        my_schedule_details=my_schedule_details,
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
        # Validate fields
        if not (name and enrollment and email and address and password):
            flash("Please fill all fields.", "danger")
            return render_template_string(SIGNUP_TEMPLATE)
        if email in users:
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for('login'))
        # prevent duplicate enrollment numbers
        if find_user_by_enrollment(enrollment):
            flash("Enrollment number already used. If this is you, please login.", "warning")
            return redirect(url_for('login'))
        pw_hash = generate_password_hash(password)
        users[email] = {"name": name, "password_hash": pw_hash, "enrollment": enrollment, "address": address, "schedule": []}
        session['user'] = email
        flash(f"Account created. Welcome, {name}!", "success")
        # redirect to next (if passed) otherwise home
        next_url = request.form.get('next') or request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('home'))
    return render_template_string(SIGNUP_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # read next from args or form
    next_url = request.args.get('next') or request.form.get('next') or None

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = users.get(email)
        if not user or not check_password_hash(user['password_hash'], password):
            flash("Invalid credentials.", "danger")
            return render_template_string(LOGIN_TEMPLATE, next=next_url)
        session['user'] = email
        flash(f"Welcome back, {user['name']}!", "success")
        # safe redirect only to same-site path
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('home'))
    # GET
    return render_template_string(LOGIN_TEMPLATE, next=next_url)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out.", "info")
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    current_user = get_current_user_email()
    user = users[current_user]
    return render_template_string(PROFILE_TEMPLATE, user=user, user_email=current_user)

@app.route('/register/<int:course_id>', methods=['POST'])
@login_required
def register(course_id):
    current_user = get_current_user_email()
    course = next((c for c in courses if c['id'] == course_id), None)
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for('home'))
    user_sched = users[current_user]['schedule']
    if course_id in user_sched:
        flash(f"You are already registered for {course['code']}.", "warning")
    elif course['enrolled'] >= course['capacity']:
        flash(f"Sorry, {course['code']} is currently full.", "danger")
    else:
        course['enrolled'] += 1
        user_sched.append(course_id)
        flash(f"Successfully registered for {course['name']}!", "success")
    return redirect(url_for('home'))

@app.route('/reset', methods=['POST'])
@login_required
def reset():
    current_user = get_current_user_email()
    user_sched = users[current_user]['schedule']
    for course_id in user_sched:
        course = next((c for c in courses if c['id'] == course_id), None)
        if course:
            course['enrolled'] = max(0, course['enrolled'] - 1)
    users[current_user]['schedule'] = []
    flash("Your schedule has been cleared.", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)

