# WatchBoard

A personal board for the movies, TV shows, and anime you want to watch, and the ones you already have. Server-rendered with Flask and Jinja2, fast, mobile-friendly, and built for one thing: keeping your watchlist actually organized.

Built by **Girish D. Sakpal**.

## Features

- **Username-based accounts:** sign up and log in with a username and password, no email required.
- **Two shelves:** every title lives on your Wishlist or in your Watched list.
- **Search, filter, and sort:** filter by status or media type (film, series, anime), search titles instantly, and sort by name, date added, release year, or your rating.
- **Optional TMDB lookup:** search The Movie Database while adding a title to auto-fill its poster, year, and overview (works without it t:oo you can add anything manually).
- **Private by default:** every account's board is scoped to that account only.
- **One owner account:** an optional "owner" login, configured purely through environment variables, with no database row of its own.
- **Responsive UI:** a clean, modern interface that works just as well on a phone as it does on a desktop.
- **Dark / light mode:** a persisted theme toggle in the navbar, applied before first paint to avoid a flash of the wrong theme.
- **Insights dashboard:** a dedicated analytics page (`/board/insights`) that computes completion rate, average rating, rating distribution, genre breakdown, and month-over-month adding/watching activity from your own data, rendered with Chart.js.

## Tech stack

- **Backend:** Flask 3, Jinja2 templates
- **Auth:** JWT stored in an httpOnly cookie, passwords hashed with bcrypt
- **Database:** SQLite for local development, PostgreSQL in production, picked automatically from `DATABASE_URL`, using `psycopg` (v3)
- **Rate limiting:** Flask-Limiter on auth endpoints
- **Frontend:** Plain HTML/CSS/JS

## Getting started

### 1. Clone and install dependencies

```bash
git clone <your-fork-url>
cd WatchBoard
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

| Variable          | Required | Description                                                                 |
|-------------------|----------|-------------------------------------------------------------------------------|
| `JWT_SECRET`      | Yes      | Long random string used to sign session tokens. App refuses to start without it. |
| `DATABASE_URL`    | No       | Defaults to a local SQLite file. Set to a `postgres://...` URL in production. |
| `OWNER_USERNAME`  | No       | Username for a personal "owner" login, checked against env vars only.        |
| `OWNER_PASSWORD`  | No       | Password for the owner login. Both `OWNER_USERNAME` and `OWNER_PASSWORD` must be set to enable it. |
| `OWNER_NAME`      | No       | Display name shown for the owner account.                                     |
| `TMDB_API_KEY`    | No       | Enables the title search/autofill box on the "Add entry" page.               |
| `FLASK_ENV`       | No       | `development` (default) or `production`. Controls whether the session cookie is marked `Secure`. |
| `PORT`            | No       | Port the dev server listens on. Defaults to `5000`.                          |
| `DATABASE_SSL`    | No       | Set to `false` to disable SSL when connecting to Postgres. Defaults to `true`.|

### 3. Run it

```bash
python run.py
```

The app starts at `http://localhost:5000` and creates its tables automatically on first run.

## Project structure

```
app/
├── db/             # Database abstraction + SQLite/Postgres schemas
├── routes/         # Blueprints: auth, board, marketing, titles
├── static/         # CSS and JS, one stylesheet per page
├── templates/      # Jinja2 templates
├── utils/          # JWT helpers, auth decorator, current-user resolver
└── __init__.py     # App factory
```

## Authentication

Accounts are created with a **username** (3–30 characters: letters, numbers, dots, underscores, or hyphens), a display name, and a password (minimum 8 characters). Passwords are hashed with bcrypt before storage. On login, a signed JWT is set as an httpOnly cookie and used to identify the user on every request, there's no server-side session store to manage.

## Deployment

WatchBoard is designed to deploy cleanly to platforms like Render: set `DATABASE_URL` to a Postgres connection string, set `FLASK_ENV=production`, provide the required environment variables above, and run with `gunicorn run:app`. Postgres connectivity is provided by `psycopg` (v3), no separate setup needed beyond installing `requirements.txt`.

## License

This project is shared for personal and educational use. Feel free to fork it and adapt it for your own watchlist.
