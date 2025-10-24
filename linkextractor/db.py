import os

from dotenv import load_dotenv
load_dotenv()

DB_URL = os.getenv("DB_URL")
DB_BACKEND = "postgres"

# _DB_URL = None
# _DB_BACKEND = None

def set_db_url(_db_url: str):
    global DB_URL, DB_BACKEND

    if _db_url is None:
        raise ValueError("db_url must have a value")

    # _config["DB_URL"] = db_url
    if _db_url.startswith("sqlite://"):
        DB_BACKEND = "sqlite"
        if _db_url.startswith("sqlite:///"):
            # Relative path
            DB_URL = _db_url[10:]  # remove 'sqlite:///'
        elif _db_url.startswith("sqlite:////"):
            # Absolute path
            DB_URL = _db_url[9:]  # remove 'sqlite:'
        else:
            raise ValueError(f"Invalid SQLite URI: {_db_url}")
    elif _db_url.startswith("postgres://"):
        DB_BACKEND = "postgres"
    else:
        raise ValueError(f"Invalid DB_URL: {_db_url}")

if DB_URL is not None:
    set_db_url(DB_URL)

_conn = None

def get_conn():
    global _conn
    if _conn is not None:
        return _conn

    if DB_URL is None:
       raise ValueError("DB_URL not set")
    if DB_BACKEND is None:
       raise ValueError("DB_BACKEND not set")

    if DB_BACKEND == "sqlite":
        import sqlite3
        _conn = sqlite3.connect(DB_URL, check_same_thread=False)
    elif DB_BACKEND == "postgres":  # postgresql
        import psycopg2
        _conn = psycopg2.connect(DB_URL, connect_timeout=5)
    else:
        raise ValueError(f"Invalid DB_BACKEND: {DB_BACKEND}")

    return _conn
