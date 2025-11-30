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
                <h5 class="card-title">{{ course.code }}: {{ course.name }}
