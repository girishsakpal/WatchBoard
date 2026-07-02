import os
import re
from collections import Counter
from datetime import datetime, date

from flask import Blueprint, request, render_template, redirect, url_for, flash, g

from app.db.database import get_db
from app.utils.auth_decorators import require_auth

bp = Blueprint("board", __name__, url_prefix="/board")

ALLOWED_MEDIA_TYPES = {"movie", "tv", "anime"}
ALLOWED_STATUSES = {"wishlist", "watched"}
ALLOWED_SORTS = {
    "title_asc": "title COLLATE NOCASE ASC",
    "title_desc": "title COLLATE NOCASE DESC",
    "date_added_desc": "date_added DESC",
    "date_added_asc": "date_added ASC",
    "year_desc": "year DESC",
    "rating_desc": "rating DESC",
}
ALLOWED_SORTS_POSTGRES = {
    "title_asc": "LOWER(title) ASC",
    "title_desc": "LOWER(title) DESC",
    "date_added_desc": "date_added DESC",
    "date_added_asc": "date_added ASC",
    "year_desc": "year DESC NULLS LAST",
    "rating_desc": "rating DESC NULLS LAST",
}


def _order_by_clause(sort_key):
    from app.db.database import get_backend_name
    table = ALLOWED_SORTS_POSTGRES if get_backend_name() == "postgres" else ALLOWED_SORTS
    return table.get(sort_key, table["title_asc"])


@bp.route("/")
@require_auth()
def dashboard():
    user_id = g.user["user_id"]
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    media_type = request.args.get("media_type", "")
    sort = request.args.get("sort", "title_asc")

    conditions = ["user_id = ?"]
    params = [user_id]

    if q:
        conditions.append("LOWER(title) LIKE ?")
        params.append(f"%{q.lower()}%")
    if status in ALLOWED_STATUSES:
        conditions.append("status = ?")
        params.append(status)
    if media_type in ALLOWED_MEDIA_TYPES:
        conditions.append("media_type = ?")
        params.append(media_type)

    order_by = _order_by_clause(sort)
    query = f"""
        SELECT * FROM entries
        WHERE {' AND '.join(conditions)}
        ORDER BY {order_by}
    """

    with get_db() as db:
        entries, _ = db.execute(query, params)
        all_rows, _ = db.execute("SELECT status FROM entries WHERE user_id = ?", [user_id])

    counts = {
        "total": len(all_rows),
        "wishlist": sum(1 for r in all_rows if r["status"] == "wishlist"),
        "watched": sum(1 for r in all_rows if r["status"] == "watched"),
    }

    return render_template(
        "dashboard.html",
        entries=entries,
        counts=counts,
        q=q, status=status, media_type=media_type, sort=sort,
    )


def _validate_entry_form(form, partial=False):
    title = form.get("title")
    media_type = form.get("media_type")
    status = form.get("status")
    rating = form.get("rating")

    if (not partial) or ("title" in form):
        if not title or not title.strip():
            return "Give it a title."
    if (not partial) or ("media_type" in form):
        if media_type not in ALLOWED_MEDIA_TYPES:
            return "Pick movie, tv, or anime."
    if (not partial) or ("status" in form):
        if status not in ALLOWED_STATUSES:
            return "Status must be wishlist or watched."
    if rating not in (None, ""):
        try:
            r = int(rating)
        except (TypeError, ValueError):
            return "Rating must be a whole number from 1 to 10."
        if r < 1 or r > 10:
            return "Rating must be a whole number from 1 to 10."
    return None


@bp.route("/new", methods=["GET", "POST"])
@require_auth()
def new_entry():
    if request.method == "GET":
        return render_template(
            "entry_form.html", entry=None, action_url=url_for("board.new_entry"),
            tmdb_enabled=bool(os.environ.get("TMDB_API_KEY")),
        )

    error = _validate_entry_form(request.form)
    if error:
        flash(error, "error")
        return render_template("entry_form.html", entry=request.form, action_url=url_for("board.new_entry")), 400

    user_id = g.user["user_id"]
    title = request.form["title"].strip()
    media_type = request.form["media_type"]
    status = request.form["status"]
    poster_url = request.form.get("poster_url") or None
    overview = request.form.get("overview") or None
    year = request.form.get("year") or None
    genres = request.form.get("genres") or None
    rating = request.form.get("rating") or None
    notes = request.form.get("notes") or None
    tmdb_id = request.form.get("tmdb_id") or None

    date_watched_clause = "datetime('now')" if status == "watched" else "NULL"

    with get_db() as db:
        from app.db.database import get_backend_name
        if get_backend_name() == "postgres":
            date_watched_sql = "NOW()" if status == "watched" else "NULL"
            db.execute(
                f"""
                INSERT INTO entries
                    (user_id, title, media_type, status, poster_url, overview,
                     year, genres, rating, notes, tmdb_id, date_watched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {date_watched_sql})
                """,
                [user_id, title, media_type, status, poster_url, overview,
                 year, genres, rating, notes, tmdb_id],
            )
        else:
            db.execute(
                f"""
                INSERT INTO entries
                    (user_id, title, media_type, status, poster_url, overview,
                     year, genres, rating, notes, tmdb_id, date_watched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {date_watched_clause})
                """,
                [user_id, title, media_type, status, poster_url, overview,
                 year, genres, rating, notes, tmdb_id],
            )

    flash(f'"{title}" added to your board.', "success")
    return redirect(url_for("board.dashboard"))


@bp.route("/<int:entry_id>/edit", methods=["GET", "POST"])
@require_auth()
def edit_entry(entry_id):
    user_id = g.user["user_id"]

    with get_db() as db:
        rows, _ = db.execute("SELECT * FROM entries WHERE id = ? AND user_id = ?", [entry_id, user_id])
    if not rows:
        flash("Entry not found.", "error")
        return redirect(url_for("board.dashboard")), 404
    entry = rows[0]

    if request.method == "GET":
        return render_template("entry_form.html", entry=entry, action_url=url_for("board.edit_entry", entry_id=entry_id))

    error = _validate_entry_form(request.form)
    if error:
        flash(error, "error")
        return render_template("entry_form.html", entry=request.form, action_url=url_for("board.edit_entry", entry_id=entry_id)), 400

    title = request.form["title"].strip()
    media_type = request.form["media_type"]
    status = request.form["status"]
    poster_url = request.form.get("poster_url") or None
    overview = request.form.get("overview") or None
    year = request.form.get("year") or None
    genres = request.form.get("genres") or None
    rating = request.form.get("rating") or None
    notes = request.form.get("notes") or None

    from app.db.database import get_backend_name
    now_fn = "NOW()" if get_backend_name() == "postgres" else "datetime('now')"

    # Keep date_watched honest: set it the moment status flips to watched
    # (unless already set), clear it if it flips back to wishlist.
    if status == "watched":
        date_watched_sql = f"COALESCE(date_watched, {now_fn})"
    else:
        date_watched_sql = "NULL"

    with get_db() as db:
        db.execute(
            f"""
            UPDATE entries SET
                title = ?, media_type = ?, status = ?, poster_url = ?, overview = ?,
                year = ?, genres = ?, rating = ?, notes = ?,
                date_watched = {date_watched_sql}, updated_at = {now_fn}
            WHERE id = ? AND user_id = ?
            """,
            [title, media_type, status, poster_url, overview, year, genres, rating, notes, entry_id, user_id],
        )

    flash(f'"{title}" updated.', "success")
    return redirect(url_for("board.dashboard"))


@bp.route("/<int:entry_id>/toggle-status", methods=["POST"])
@require_auth()
def toggle_status(entry_id):
    user_id = g.user["user_id"]
    with get_db() as db:
        rows, _ = db.execute("SELECT status FROM entries WHERE id = ? AND user_id = ?", [entry_id, user_id])
        if not rows:
            flash("Entry not found.", "error")
            return redirect(url_for("board.dashboard")), 404

        new_status = "wishlist" if rows[0]["status"] == "watched" else "watched"
        from app.db.database import get_backend_name
        now_fn = "NOW()" if get_backend_name() == "postgres" else "datetime('now')"
        date_watched_sql = f"COALESCE(date_watched, {now_fn})" if new_status == "watched" else "NULL"

        db.execute(
            f"UPDATE entries SET status = ?, date_watched = {date_watched_sql}, updated_at = {now_fn} "
            f"WHERE id = ? AND user_id = ?",
            [new_status, entry_id, user_id],
        )

    return redirect(request.referrer or url_for("board.dashboard"))


@bp.route("/<int:entry_id>/delete", methods=["POST"])
@require_auth()
def delete_entry(entry_id):
    user_id = g.user["user_id"]
    with get_db() as db:
        rows, _ = db.execute("SELECT title FROM entries WHERE id = ? AND user_id = ?", [entry_id, user_id])
        if not rows:
            flash("Entry not found.", "error")
            return redirect(url_for("board.dashboard")), 404
        title = rows[0]["title"]
        db.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", [entry_id, user_id])

    flash(f'"{title}" removed from your board.', "success")
    return redirect(url_for("board.dashboard"))


MEDIA_LABELS = {"movie": "Film", "tv": "Series", "anime": "Anime"}


def _to_datetime(value):
    """Normalize a SQLite date string or a Postgres datetime/date into a
    plain datetime, or None if the value is missing/unparseable."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    try:
        return datetime.fromisoformat(str(value)[:19].replace(" ", "T"))
    except ValueError:
        return None


def _month_key(dt):
    return f"{dt.year:04d}-{dt.month:02d}" if dt else None


@bp.route("/insights")
@require_auth()
def insights():
    user_id = g.user["user_id"]
    with get_db() as db:
        rows, _ = db.execute("SELECT * FROM entries WHERE user_id = ?", [user_id])

    total = len(rows)
    watched_rows = [r for r in rows if r["status"] == "watched"]
    wishlist_rows = [r for r in rows if r["status"] == "wishlist"]
    completion_rate = round((len(watched_rows) / total) * 100) if total else 0

    # --- Media type breakdown ---
    media_counts = Counter(r["media_type"] for r in rows)
    media_breakdown = [
        {"key": k, "label": MEDIA_LABELS.get(k, k), "count": media_counts.get(k, 0)}
        for k in ("movie", "tv", "anime")
    ]

    # --- Ratings: average + 1-10 histogram ---
    ratings = [r["rating"] for r in rows if r["rating"]]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None
    rating_hist = Counter(ratings)
    rating_distribution = [rating_hist.get(i, 0) for i in range(1, 11)]

    # --- Genres: free-text, comma/slash separated ---
    genre_counter = Counter()
    for r in rows:
        if r["genres"]:
            for name in re.split(r"[,/]", r["genres"]):
                name = name.strip()
                if name:
                    genre_counter[name] += 1
    top_genres = genre_counter.most_common(8)
    max_genre_count = top_genres[0][1] if top_genres else 0

    # --- Monthly activity: added vs watched, trailing 12 months ---
    now = datetime.utcnow()
    months = []
    y, m = now.year, now.month
    for _ in range(12):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months.reverse()

    added_by_month = Counter(_month_key(_to_datetime(r["date_added"])) for r in rows)
    watched_by_month = Counter(
        _month_key(_to_datetime(r["date_watched"])) for r in rows if r["date_watched"]
    )
    monthly_added = [added_by_month.get(mo, 0) for mo in months]
    monthly_watched = [watched_by_month.get(mo, 0) for mo in months]
    month_labels = [datetime.strptime(mo, "%Y-%m").strftime("%b") for mo in months]
    max_monthly = max(monthly_added + monthly_watched or [0])

    # --- Average time from adding to watching ---
    lead_times = []
    for r in watched_rows:
        added = _to_datetime(r["date_added"])
        watched = _to_datetime(r["date_watched"])
        if added and watched:
            delta_days = (watched - added).days
            if delta_days >= 0:
                lead_times.append(delta_days)
    avg_days_to_watch = round(sum(lead_times) / len(lead_times)) if lead_times else None

    top_rated = sorted(
        [r for r in rows if r["rating"]], key=lambda r: r["rating"], reverse=True
    )[:5]

    return render_template(
        "insights.html",
        total=total,
        watched_count=len(watched_rows),
        wishlist_count=len(wishlist_rows),
        completion_rate=completion_rate,
        media_breakdown=media_breakdown,
        avg_rating=avg_rating,
        rated_count=len(ratings),
        rating_distribution=rating_distribution,
        top_genres=top_genres,
        max_genre_count=max_genre_count,
        month_labels=month_labels,
        monthly_added=monthly_added,
        monthly_watched=monthly_watched,
        max_monthly=max_monthly,
        avg_days_to_watch=avg_days_to_watch,
        top_rated=top_rated,
    )
