from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from db import authenticate_user, execute, query_one

auth_bp = Blueprint("auth", __name__)


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return function(*args, **kwargs)

    return wrapper


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    user = authenticate_user(request.form.get("username"), request.form.get("password"))
    if user:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        return redirect(url_for("pages.dashboard"))

    return render_template("login.html", error="Invalid credentials")


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username")
    password = request.form.get("password")
    role = request.form.get("role")
    if query_one("SELECT * FROM users WHERE username=?", (username,)):
        return render_template("register.html", error="Username already exists")

    execute(
        "INSERT INTO users(username, password, role) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), role),
    )
    return redirect(url_for("auth.login"))