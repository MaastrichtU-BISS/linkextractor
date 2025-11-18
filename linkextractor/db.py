import os
from typing import Iterator
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extensions import connection
from contextlib import contextmanager
from dotenv import load_dotenv
load_dotenv()

DB_URL = os.getenv("LINKEXTRACTOR_DB_URL")

def set_db_url(_db_url):
    global DB_URL
    DB_URL = _db_url

def get_conn():
    return psycopg2.connect(DB_URL, connect_timeout=5)