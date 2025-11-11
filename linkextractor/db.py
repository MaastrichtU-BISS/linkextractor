import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv
load_dotenv()

DB_URL = os.getenv("LINKEXTRACTOR_DB_URL")

def set_db_url(_db_url: str):
    global DB_URL, DB_BACKEND

    if _db_url is None:
        raise ValueError("db_url must have a value")
    elif _db_url.startswith("postgres://"):
        DB_BACKEND = "postgres"
        DB_URL = _db_url[9:]
    else:
        raise ValueError(f"Invalid DB_URL: {_db_url}")

# if DB_URL is not None:
#     set_db_url(DB_URL)

_conn = None

def get_conn():
    global _conn
    if _conn is not None:
        return _conn

    if DB_URL is None:
       raise ValueError("DB_URL not set")

    import psycopg2
    
    _conn = psycopg2.connect(DB_URL, connect_timeout=5)

    return _conn
