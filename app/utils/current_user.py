
import os
import jwt as pyjwt
from flask import request, g

from app.utils.jwt_utils import verify_token
from app.db.database import get_db


def get_current_user():
    if hasattr(g, "_current_user_cache"):
        return g._current_user_cache

    token = request.cookies.get("token")
    user = None
    if token:
        try:
            decoded = verify_token(token)
            if decoded.get("is_owner"):
                user = {
                    "id": 0,
                    "name": decoded.get("name") or os.environ.get("OWNER_NAME", "Girish D. Sakpal"),
                    "username": os.environ.get("OWNER_USERNAME"),
                    "is_owner": True,
                }
            else:
                with get_db() as db:
                    rows, _ = db.execute(
                        "SELECT id, name, username FROM users WHERE id = ?",
                        [decoded["user_id"]],
                    )
                if rows:
                    user = {**rows[0], "is_owner": False}
        except pyjwt.PyJWTError:
            user = None

    g._current_user_cache = user
    return user
