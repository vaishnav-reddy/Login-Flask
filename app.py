from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-prod")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --------- Database Model ---------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)    

# --------- Helper: login_required ---------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# --------- Routes ---------
@app.route("/")
def home():
    return redirect(url_for("dashboard") if "user_id" in session else "login")

@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not email or not password or not confirm:
            msg = "Please fill all fields."
        elif password != confirm:
            msg = "Passwords do not match."
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            msg = "Username or email already exists."
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("login", registered="1"))
    return render_template("register.html", msg=msg)

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = "Registration successful. Please log in." if request.args.get("registered") else ""
    if request.method == "POST":
        email_or_username = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(
            (User.email == email_or_username) | (User.username == email_or_username)
        ).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("dashboard"))
        else:
            msg = "Invalid credentials."
    return render_template("login.html", msg=msg)

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session.get("username"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    user = User.query.get(session["user_id"])
    if user:
        db.session.delete(user)
        db.session.commit()
        session.clear()  # log them out after deleting
    return redirect(url_for("register"))


# Create DB tables when app starts
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
