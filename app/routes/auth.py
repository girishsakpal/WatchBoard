import os
import re
from datetime import timedelta

import bcrypt
from flask import Blueprint, request, render_template, redirect, url_for, make_response, flash
from flask_limiter.util import get_remote_address

from app.db.database import get_db
from app.utils.jwt_utils import sign_token
from app.extensions import limiter

bp = Blueprint("auth", __name__, url_prefix="/auth")

# Letters, numbers, underscores, dots and hyphens. 3-30 chars.
USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,30}$")
COOKIE_MAX_AGE = int(timedelta(days=7).total_seconds())


def _cookie_kwargs():
    is_prod = os.environ.get("FLASK_ENV") == "production"
    return {
        "httponly": True,
        "secure": is_prod,
        "samesite": "Lax",
        "max_age": COOKIE_MAX_AGE,
        "path": "/",
    }


def _rate_key():
    return get_remote_address()


@bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("20 per 15 minutes", key_func=_rate_key, methods=["POST"])
def signup_page():
    if request.method == "GET":
        return render_template("signup.html")

    name = (request.form.get("name") or "").strip()
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""

    if not name:
        flash("Enter your name.", "error")
        return render_template("signup.html", name=name, username=username), 400
    if not username or not USERNAME_RE.match(username):
        flash("Username must be 3-30 characters: letters, numbers, dots, underscores, or hyphens.", "error")
        return render_template("signup.html", name=name, username=username), 400
    if not password or len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return render_template("signup.html", name=name, username=username), 400

    with get_db() as db:
        existing, _ = db.execute("SELECT id FROM users WHERE username = ?", [username])
        if existing:
            flash("That username is already taken.", "error")
            return render_template("signup.html", name=name, username=username), 409

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
        _, new_id = db.execute(
            "INSERT INTO users (name, username, password_hash) VALUES (?, ?, ?)",
            [name, username, password_hash],
        )
        if new_id is None:
            # Fallback in case lastrowid wasn't populated; look the row back up.
            rows, _ = db.execute("SELECT id FROM users WHERE username = ?", [username])
            new_id = rows[0]["id"]

    token = sign_token({"user_id": new_id, "is_owner": False})
    resp = make_response(redirect(url_for("board.dashboard")))
    resp.set_cookie("token", token, **_cookie_kwargs())
    flash(f"Welcome, {name}, your board is ready.", "success")
    return resp


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per 15 minutes", key_func=_rate_key, methods=["POST"])
def login_page():
    if request.method == "GET":
        return render_template("login.html", next_path=request.args.get("next", ""))

    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""
    next_path = request.form.get("next") or url_for("board.dashboard")

    if not username or not password:
        flash("Enter your username and password.", "error")
        return render_template("login.html", username=username, next_path=next_path), 400

    # --- Owner path: checked first, against env vars only. No DB row, ever. ---
    owner_username = (os.environ.get("OWNER_USERNAME") or "").strip().lower()
    owner_password = os.environ.get("OWNER_PASSWORD")

    if owner_username and owner_password and username == owner_username:
        if password == owner_password:
            owner_name = os.environ.get("OWNER_NAME", "Girish D. Sakpal")
            token = sign_token({"user_id": 0, "is_owner": True, "name": owner_name})
            resp = make_response(redirect(next_path))
            resp.set_cookie("token", token, **_cookie_kwargs())
            flash(f"Welcome back, {owner_name}.", "success")
            return resp
        flash("Incorrect username or password.", "error")
        return render_template("login.html", username=username, next_path=next_path), 401

    # --- Normal user path ---
    with get_db() as db:
        rows, _ = db.execute(
            "SELECT id, name, username, password_hash FROM users WHERE username = ?",
            [username],
        )

    user = rows[0] if rows else None
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        flash("Incorrect username or password.", "error")
        return render_template("login.html", username=username, next_path=next_path), 401

    token = sign_token({"user_id": user["id"], "is_owner": False})
    resp = make_response(redirect(next_path))
    resp.set_cookie("token", token, **_cookie_kwargs())
    flash(f"Welcome back, {user['name']}.", "success")
    return resp


@bp.route("/logout", methods=["POST"])
def logout():
    resp = make_response(redirect(url_for("marketing.landing")))
    resp.set_cookie("token", "", expires=0, path="/")
    flash("You've been logged out.", "success")
    return resp
