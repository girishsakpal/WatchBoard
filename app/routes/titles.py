import os
import requests
from flask import Blueprint, request, jsonify

from app.utils.auth_decorators import require_auth

bp = Blueprint("titles", __name__, url_prefix="/api/titles")

TMDB_BASE = "https://api.themoviedb.org/3"


@bp.route("/search", methods=["GET"])
@require_auth(json_response=True)
def search_titles():
    api_key = os.environ.get("TMDB_API_KEY")
    if not api_key:
        return jsonify({"error": "Title search is not configured on this server yet."}), 503

    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Type something to search for."}), 400

    try:
        response = requests.get(
            f"{TMDB_BASE}/search/multi",
            params={"api_key": api_key, "query": q, "include_adult": "false"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return jsonify({"error": "Could not reach the title database right now."}), 502

    results = []
    for item in data.get("results", []):
        media_type = item.get("media_type")
        if media_type not in ("movie", "tv"):
            continue
        poster_path = item.get("poster_path")
        results.append({
            "tmdb_id": item.get("id"),
            "title": item.get("title") or item.get("name"),
            "media_type": media_type,
            "year": (item.get("release_date") or item.get("first_air_date") or "")[:4] or None,
            "overview": item.get("overview") or "",
            "poster_url": f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else None,
        })
        if len(results) >= 12:
            break

    return jsonify({"results": results})
