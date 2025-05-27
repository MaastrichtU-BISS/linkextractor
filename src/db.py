import os

from dotenv import load_dotenv
load_dotenv()

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")
DB_URL     = os.getenv("DB_URL", "data.db")

_conn = None

def get_conn():
    global _conn
    if _conn is not None:
        return _conn

    if DB_BACKEND == "sqlite":
        import sqlite3
        _conn = sqlite3.connect(DB_URL, check_same_thread=False)
    elif DB_BACKEND == "postgres":  # postgresql
        import psycopg2
        _conn = psycopg2.connect(DB_URL, connect_timeout=5)
    else:
        raise Exception(f"Invalid DB_BACKEND: {DB_BACKEND}")

    return _conn