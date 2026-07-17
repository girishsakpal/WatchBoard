-- WatchBoard schema (SQLite for local development)
-- Built by Girish D. Sakpal

CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS entries (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id      INTEGER NOT NULL,
  title        TEXT NOT NULL,
  media_type   TEXT NOT NULL CHECK (media_type IN ('movie', 'tv', 'anime')),
  status       TEXT NOT NULL CHECK (status IN ('wishlist', 'watched')) DEFAULT 'wishlist',
  poster_url   TEXT,
  overview     TEXT,
  year         INTEGER,
  genres       TEXT,
  platforms    TEXT,
  rating       INTEGER CHECK (rating IS NULL OR (rating BETWEEN 1 AND 10)),
  notes        TEXT,
  tmdb_id      INTEGER,
  date_added   TEXT NOT NULL DEFAULT (datetime('now')),
  date_watched TEXT,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_entries_user_id ON entries(user_id);
CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(user_id, status);
CREATE INDEX IF NOT EXISTS idx_entries_title ON entries(user_id, title);
CREATE INDEX IF NOT EXISTS idx_entries_media_type ON entries(user_id, media_type);
