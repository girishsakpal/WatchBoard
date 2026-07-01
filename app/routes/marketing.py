from flask import Blueprint, render_template, redirect, url_for
from app.utils.current_user import get_current_user

bp = Blueprint("marketing", __name__)


@bp.route("/")
def landing():
    user = get_current_user()
    if user:
        return redirect(url_for("board.dashboard"))
    return render_template("landing.html")
