"""
require_auth: reads the httpOnly `token` cookie, verifies it, and stashes
the decoded payload on flask.g.user for the view to use.

Since this app is server-rendered (Jinja2, not a JSON SPA), an
unauthenticated visit to a protected page should redirect to /login —
not return a bare 401 the browser can't do anything with. The one
exception is /api/titles/search, which is called via fetch() from a
page's own JavaScript and genuinely wants JSON back; pass
json_response=True for those.
"""
from functools import wraps
import jwt as pyjwt
from flask import request, redirect, url_for, flash, jsonify, g

from app.utils.jwt_utils import verify_token


def require_auth(json_response=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.cookies.get("token")
            if not token:
                if json_response:
                    return jsonify({"error": "You need to sign in to do that."}), 401
                flash("Please log in to continue.", "error")
                return redirect(url_for("auth.login_page", next=request.path))
            try:
                decoded = verify_token(token)
            except pyjwt.PyJWTError:
                if json_response:
                    return jsonify({"error": "Your session has expired. Please sign in again."}), 401
                flash("Your session has expired. Please log in again.", "error")
                return redirect(url_for("auth.login_page"))
            g.user = decoded
            return fn(*args, **kwargs)

        return wrapper

    return decorator
