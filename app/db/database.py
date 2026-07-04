import os
import sqlite3
from contextlib import contextmanager

_backend = None 

def _resolve_backend():
    global _backend
    if _backend is not None:
        return _backend

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
        _backend = "postgres"
    else:
        _backend = "sqlite"
    return _backend


def get_backend_name():
    return _resolve_backend()


def _sqlite_path():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url.startswith("sqlite:///"):
        return database_url[len("sqlite:///"):]
    if database_url.startswith("sqlite://"):
        return database_url[len("sqlite://"):]
    
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "watchboard.db")


def _qmark_to_pyformat(query: str) -> str:
    return query.replace("?", "%s")


class _DictRowConnection:
    def __init__(self, backend):
        self.backend = backend
        if backend == "sqlite":
            path = _sqlite_path()
            self._conn = sqlite3.connect(path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = OFF")
        else:
            import psycopg
            from psycopg.rows import dict_row
            database_url = os.environ["DATABASE_URL"]
            use_ssl = os.environ.get("DATABASE_SSL", "true").lower() != "false"
            conninfo = database_url
            if use_ssl and "sslmode=" not in database_url:
                sep = "&" if "?" in database_url else "?"
                conninfo = f"{database_url}{sep}sslmode=require"
            self._conn = psycopg.connect(conninfo, row_factory=dict_row)

    def execute(self, query, params=None):
        params = params or []
        if self.backend == "sqlite":
            cur = self._conn.cursor()
            cur.execute(query, params)
            if cur.description:
                rows = [dict(row) for row in cur.fetchall()]
            else:
                rows = []
            lastrowid = cur.lastrowid
            cur.close()
            return rows, lastrowid
        else:
            pg_query = _qmark_to_pyformat(query)
            cur = self._conn.cursor()
            cur.execute(pg_query, params)
            if cur.description:
                rows = [dict(row) for row in cur.fetchall()]
            else:
                rows = []
            cur.close()
            return rows, None

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


@contextmanager
def get_db():
    backend = _resolve_backend()
    conn = _DictRowConnection(backend)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_last_active_column(db, backend):
    if backend == "sqlite":
        rows, _ = db.execute("PRAGMA table_info(users)")
        existing_columns = {row["name"] for row in rows}
        if "last_active_at" not in existing_columns:
            db._conn.execute("ALTER TABLE users ADD COLUMN last_active_at TEXT")
    else:
        cur = db._conn.cursor()
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ")
        cur.close()


def init_schema():
    backend = _resolve_backend()
    schema_file = "schema_sqlite.sql" if backend == "sqlite" else "schema_postgres.sql"
    schema_path = os.path.join(os.path.dirname(__file__), schema_file)
    with open(schema_path) as f:
        schema_sql = f.read()

    with get_db() as db:
        if backend == "sqlite":
            db._conn.executescript(schema_sql)
        else:
            cur = db._conn.cursor()
            cur.execute(schema_sql)
            cur.close()
        _ensure_last_active_column(db, backend)
