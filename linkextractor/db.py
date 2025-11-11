import os
from typing import Iterator
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extensions import connection
from contextlib import contextmanager
from dotenv import load_dotenv
load_dotenv()

DB_URL = os.getenv("LINKEXTRACTOR_DB_URL")

MIN_CONN = 1
MAX_CONN = 5

_pool = None

def set_db_url(_db_url):
    global DB_URL
    DB_URL = _db_url

def _get_pool():
    """Lazy-initialize the pool."""
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(
            MIN_CONN,
            MAX_CONN,
            DB_URL
        )
    return _pool


@contextmanager
def get_conn() -> Iterator[connection]:
    """
    Usage:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)