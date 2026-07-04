from datetime import datetime, date

from flask import Blueprint, render_template, g, abort

from app.db.database import get_db
from app.utils.auth_decorators import require_auth

bp = Blueprint("owner", __name__, url_prefix="/owner")


def _to_datetime(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    try:
        return datetime.fromisoformat(str(value)[:26].replace(" ", "T"))
    except ValueError:
        return None


@bp.route("/panel")
@require_auth()
def panel():
    # Not the owner? This route doesn't exist as far as you're concerned.
    if not g.user.get("is_owner"):
        abort(404)

    with get_db() as db:
        rows, _ = db.execute(
            "SELECT id, name, username, created_at, last_active_at FROM users"
        )

    now = datetime.utcnow()
    users = []
    for row in rows:
        last_active = _to_datetime(row["last_active_at"])
        online_now = bool(last_active and (now - last_active).total_seconds() < 300)
        users.append({**row, "_last_active_dt": last_active, "online_now": online_now})

    users.sort(key=lambda u: (u["_last_active_dt"] is not None, u["_last_active_dt"]), reverse=True)

    online_count = sum(1 for u in users if u["online_now"])

    return render_template("owner_panel.html", users=users, online_count=online_count)
