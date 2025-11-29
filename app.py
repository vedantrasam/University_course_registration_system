# app.py
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'university_secret_key'  # demo only

# ---------- In-memory data (demo) ----------
users = {}  # users[email] = {name, password_hash, enrollment, address, schedule: []}

courses = [
    {"id": 101, "code": "AM2301", "name": "Applied Mathematics", "prof": "Mrs Shrawani Mitkari", "credits": 4, "capacity": 30, "enrolled": 0},
    {"id": 102, "code": "CSE2304", "name": "Data Structures", "prof": "Mrs Monalisa Hati", "credits": 3, "capacity": 50, "enrolled": 0},
    {"id": 103, "code": "FL-301", "name": "Foreign Language", "prof": "Mrs Surekha Athawade", "credits": 4, "capacity": 40, "enrolled": 0},
    {"id": 104, "code": "DSD2303", "name": "Digital logic and Computer Architecture", "prof": "Mrs Saranya Pandian", "credits": 3, "capacity": 25, "enrolled": 0},
    {"id": 105, "code": "CSE2302", "name": "Data Base Management system", "prof": "Dr Dipak Raskar", "credits": 2, "capacity": 60, "enrolled": 0},
    {"id": 106, "code": "CSE2308", "name": "Java Programming", "prof": "Dr Deepika Shekhawat", "credits": 3, "capacity": 30, "enrolled": 0}
]

# ---------- Helpers ----------
def get_current_user_email():
    return session.get('user')

def get_user(email):
    return users.get(email)

def get_user_schedule(email):
    u = get_user(email)
    return u.get('schedule', []) if u else []

def find_user_by_enrollment(no):
    for e,u in users.items():
        if u.get('enrollment') == no:
            return e
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user_email():
            # preserve requested path
            next_url = request.full_path.rstrip('?')
            return redirect(url_for('auth_page', next=next_url))
        return f(*args, **kwargs)
    return decorated

# ---------- Templates ----------
# Small shared navbar
NAV_HTML = """
<nav class="navbar navbar-expand-lg navbar-dark mb-4" style="background:#2c3e50;">
  <div class="container">
    <a class="navbar-brand" href="/">🏛️ UniReg</a>
    <div class="collapse navbar-collapse">
      <ul class="navbar-nav ms-auto">
        {% if current_user %}
          <li class="nav-item me-2"><span class="navbar-text text-white">Hi, <strong>{{ current_user_name }}</strong></span></li>
          <li class="nav-item me-2"><a class="btn btn-sm btn-outline-light" href="{{ url_for('courses') }}">Courses</a></li>
          <li class="nav-item"><a class="btn btn-sm btn-outline-light" href="{{ url_for('profile') }}">Profile</a></li>
          <li class="nav-item ms-2"><a class="btn btn-sm btn-light" href="{{ url_for('logout') }}">Logout</a></li>
        {% else %}
          <li class="nav-item"><a class="btn btn-sm btn-outline-light me-2" href="{{ url_for('auth_page') }}">Sign In / Sign Up</a></li>
          <li class="nav-item"><a class="btn btn-sm btn-light" href="{{ url_for('courses') }}">Courses</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>
"""

# Auth page: shows tabs for Login and Signup
AUTH_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Auth — UniReg</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  {{ nav|safe }}
  <div class="container" style="max-width:920px;">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat,msg in messages %}
          <div class="alert alert-{{cat}} alert-dismissible fade show">{{ msg }}<button class="btn-close" data-bs-dismiss="alert"></button></div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="row">
      <div class="col-md-6">
        <div class="card p-3">
          <h4>Sign In</h4>
          <form method="POST" action="{{ url_for('auth_login') }}">
            <input type="hidden" name="next" value="{{ next or '' }}">
            <div class="mb-2"><label>Email</label><input name="email" required class="form-control" type="email"></div>
            <div class="mb-2"><label>Password</label><input name="password" required class="form-control" type="password"></div>
            <button class="btn btn-primary w-100">Login</button>
          </form>
        </div>
      </div>

      <div class="col-md-6">
        <div class="card p-3">
          <h4>Sign Up</h4>
          <form method="POST" action="{{ url_for('auth_signup') }}">
            <input type="hidden" name="next" value="{{ next or '' }}">
            <div class="row">
              <div class="mb-2 col-md-6"><label>Name</label><input name="name" required class="form-control"></div>
              <div class="mb-2 col-md-6"><label>Enrollment No.</label><input name="enrollment" required class="form-control"></div>
            </div>
            <div class="mb-2"><label>Email</label><input name="email" required class="form-control" type="email"></div>
            <div class="mb-2"><label>Address</label><input name="address" required class="form-control"></div>
            <div class="mb-2"><label>Password</label><input name="password" required class="form-control" type="password"></div>
            <button class="btn btn-success w-100">Create Account</button>
          </form>
        </div>
      </div>
    </div>
  </div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Courses page (requires login to register actions)
COURSES_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Courses — UniReg</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>.card{box-shadow:0 4px 8px rgba(0,0,0,0.06);}.btn-register{width:100%}</style>
</head>
<body>
  {{ nav|safe }}
  <div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat,msg in messages %}
          <div class="alert alert-{{cat}} alert-dismissible fade show">{{ msg }}<button class="btn-close" data-bs-dismiss="alert"></button></div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="row">
      <div class="col-md-8">
        <h3>Available Courses</h3>
        <div class="row">
          {% for course in courses %}
            <div class="col-md-6 mb-3">
              <div class="card p-3">
                <h5>{{ course.code }} — {{ course.name }}</h5>
                <p class="text-muted">{{ course.prof }}</p>
                <p><strong>Seats:</strong> {{ course.enrolled }} / {{ course.capacity }} · <strong>Credits:</strong> {{ course.credits }}</p>
                <div>
                  {% if course.id in user_schedule %}
                    <button class="btn btn-secondary btn-register" disabled>Enrolled ✅</button>
                  {% elif course.enrolled >= course.capacity %}
                    <button class="btn btn-outline-danger btn-register" disabled>Full 🚫</button>
                  {% else %}
                    <form method="POST" action="{{ url_for('register', course_id=course.id) }}">
                      <button class="btn btn-primary btn-register">Register Now</button>
                    </form>
                  {% endif %}
                </div>
              </div>
            </div>
          {% endfor %}
        </div>
      </div>

      <div class="col-md-4">
        <div class="card p-3">
          <h5>My Schedule</h5>
          {% if my_schedule_details %}
            <ul class="list-group list-group-flush">
              {% for it in my_schedule_details %}
                <li class="list-group-item d-flex justify-content-between">
                  <div><strong>{{ it.code }}</strong><br><small>{{ it.name }}</small></div>
                  <span class="badge bg-primary">{{ it.credits }} Cr</span>
                </li>
              {% endfor %}
            </ul>
            <div class="mt-3"><strong>Total Credits:</strong> {{ total_credits }}</div>
            <form method="POST" action="{{ url_for('reset') }}" class="mt-3"><button class="btn btn-outline-secondary w-100">Reset Schedule</button></form>
          {% else %}
            <div class="alert alert-info">No classes yet.</div>
          {% endif %}
        </div>
      </div>

    </div>
  </div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

PROFILE_TEMPLATE = """
<!doctype html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body>
  {{ nav|safe }}
  <div class="container" style="max-width:720px;">
    <h3>My Profile</h3>
    <div class="card p-3">
      <p><strong>Name:</strong> {{ user.name }}</p>
      <p><strong>Email:</strong> {{ user_email }}</p>
      <p><strong>Enrollment:</strong> {{ user.enrollment }}</p>
      <p><strong>Address:</strong> {{ user.address }}</p>
      <a class="btn btn-secondary" href="{{ url_for('courses') }}">Back to Courses</a>
    </div>
  </div>
</body>
</html>
"""

# ---------- Routes: landing, auth, courses ----------
@app.route('/')
def index():
    current = get_current_user_email()
    return render_template_string(
        """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
        <body>{{ nav|safe }}<div class="container"><h2>Welcome to UniReg</h2>
        <p>Use the links above to Sign In / Sign Up or go to Courses.</p></div></body></html>""",
        nav=render_template_string(NAV_HTML, current_user=current, current_user_name=(users[current]['name'] if current and current in users else None))
    )

# Auth page: shows both signin and signup
@app.route('/auth')
def auth_page():
    next_url = request.args.get('next') or ''
    current = get_current_user_email()
    if current:
        return redirect(url_for('courses'))
    return render_template_string(AUTH_TEMPLATE, next=next_url, nav=render_template_string(NAV_HTML, current_user=None))

# Login (POST)
@app.route('/auth/login', methods=['POST'])
def auth_login():
    next_url = request.form.get('next') or ''
    email = request.form.get('email','').strip().lower()
    password = request.form.get('password','')
    user = users.get(email)
    if not user or not check_password_hash(user['password_hash'], password):
        flash("Invalid credentials.", "danger")
        return redirect(url_for('auth_page', next=next_url))
    session['user'] = email
    flash(f"Welcome back, {user['name']}!", "success")
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(url_for('courses'))

# Signup (POST)
@app.route('/auth/signup', methods=['POST'])
def auth_signup():
    next_url = request.form.get('next') or ''
    name = request.form.get('name','').strip()
    enrollment = request.form.get('enrollment','').strip()
    email = request.form.get('email','').strip().lower()
    address = request.form.get('address','').strip()
    password = request.form.get('password','')
    # validation
    if not (name and enrollment and email and address and password):
        flash("Fill all fields.", "danger")
        return redirect(url_for('auth_page', next=next_url))
    if email in users:
        flash("Email exists — please login.", "warning")
        return redirect(url_for('auth_page', next=next_url))
    if find_user_by_enrollment(enrollment):
        flash("Enrollment already used — please login.", "warning")
        return redirect(url_for('auth_page', next=next_url))
    pw_hash = generate_password_hash(password)
    users[email] = {"name": name, "password_hash": pw_hash, "enrollment": enrollment, "address": address, "schedule": []}
    session['user'] = email
    flash(f"Account created. Welcome, {name}!", "success")
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(url_for('courses'))

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out.", "info")
    return redirect(url_for('index'))

# Profile (requires login)
@app.route('/profile')
@login_required
def profile():
    current = get_current_user_email()
    user = users[current]
    nav = render_template_string(NAV_HTML, current_user=current, current_user_name=user['name'])
    return render_template_string(PROFILE_TEMPLATE, user=user, user_email=current, nav=nav)

# Courses page (main registration UI) - requires login to perform actions, but we allow viewing and ask to login when needed
@app.route('/courses')
def courses_page():
    current = get_current_user_email()
    if not current:
        # show guest view but link will send to auth with next
        nav = render_template_string(NAV_HTML, current_user=None)
        return redirect(url_for('auth_page', next='/courses'))
    user_schedule = get_user_schedule(current)
    my_schedule_details = [c for c in courses if c['id'] in user_schedule]
    total_credits = sum(c['credits'] for c in my_schedule_details)
    nav = render_template_string(NAV_HTML, current_user=current, current_user_name=users[current]['name'])
    return render_template_string(COURSES_TEMPLATE, nav=nav, courses=courses, user_schedule=user_schedule, my_schedule_details=my_schedule_details, total_credits=total_credits)

# Register route (POST) - requires login
@app.route('/register/<int:course_id>', methods=['POST'])
@login_required
def register(course_id):
    current = get_current_user_email()
    course = next((c for c in courses if c['id']==course_id), None)
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for('courses'))
    user_sched = users[current]['schedule']
    if course_id in user_sched:
        flash("Already enrolled.", "warning")
    elif course['enrolled'] >= course['capacity']:
        flash("Course full.", "danger")
    else:
        course['enrolled'] += 1
        user_sched.append(course_id)
        flash(f"Registered for {course['name']}.", "success")
    return redirect(url_for('courses'))

# Reset schedule - requires login
@app.route('/reset', methods=['POST'])
@login_required
def reset():
    current = get_current_user_email()
    user_sched = users[current]['schedule']
    for cid in user_sched:
        course = next((c for c in courses if c['id']==cid), None)
        if course:
            course['enrolled'] = max(0, course['enrolled'] - 1)
    users[current]['schedule'] = []
    flash("Schedule cleared.", "info")
    return redirect(url_for('courses'))

# ----------------------
if __name__ == '__main__':
    app.run(debug=True)
