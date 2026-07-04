
from functools import wraps
from datetime import datetime, timezone
import jwt as pyjwt
from flask import request, redirect, url_for, flash, jsonify, g

from app.utils.jwt_utils import verify_token
from app.db.database import get_db


def _touch_last_active(user_id):
    """Best-effort activity stamp for the owner panel. Never allowed to
    break a real request — if the DB hiccups here, the user just doesn't
    get an updated timestamp this time around."""
    try:
        with get_db() as db:
            db.execute(
                "UPDATE users SET last_active_at = ? WHERE id = ?",
                [datetime.now(timezone.utc).isoformat(sep=" "), user_id],
            )
    except Exception:
        pass


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
            if not decoded.get("is_owner"):
                _touch_last_active(decoded.get("user_id"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator
