import os
import psycopg2
from dotenv import load_dotenv

def get_conn(db_url: str = None):
    if db_url is None:
        load_dotenv()
        db_url = os.environ["DB_URL"]
    if db_url is None:
        raise Exception("Set the DB_URL environment-variable")
    return psycopg2.connect(db_url, connect_timeout=3)

def init_db(conn):
    print("Initializing database")
    cursor = conn.cursor()
    # Create table if needed (customize types and columns)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS legal_case (
        id SERIAL PRIMARY KEY,
        ecli_id TEXT UNIQUE NOT NULL,
        title TEXT,
        celex_id TEXT UNIQUE,
        zaaknummer TEXT UNIQUE,
        uitspraakdatum DATE
    );

    CREATE TABLE IF NOT EXISTS law_element (
        id SERIAL PRIMARY KEY,
        type TEXT CHECK (type IN ('wet', 'boek', 'deel', 'titeldeel', 'hoofdstuk', 'artikel', 'paragraaf', 'subparagraaf', 'afdeling')),
        bwb_id TEXT,
        bwb_label_id INTEGER,
        lido_id TEXT UNIQUE,
        jc_id TEXT UNIQUE,
        number TEXT,
        title TEXT
    );

    CREATE TABLE IF NOT EXISTS case_law (
        id SERIAL PRIMARY KEY,
        case_id INTEGER,
        law_id INTEGER,
        source TEXT CHECK (source IN ('lido-ref', 'lido-linkt', 'custom')),
        jc_id TEXT,
        lido_id TEXT,
        opschrift TEXT,
        FOREIGN KEY (case_id) REFERENCES legal_case(id),
        FOREIGN KEY (law_id) REFERENCES law_element(id)
    );

    CREATE TABLE IF NOT EXISTS law_alias (
        id SERIAL PRIMARY KEY,
        alias TEXT NOT NULL,
        law_element_id INTEGER NOT NULL,
        source TEXT CHECK (source IN ('opschrift', 'bwbidlist')),
        FOREIGN KEY (law_element_id) REFERENCES law_element(id) ON DELETE CASCADE
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_law_alias_uniq ON law_alias (LOWER(alias), law_element_id);
    CREATE INDEX IF NOT EXISTS idx_law_alias_index ON law_alias(lower(alias));
    """)
    conn.commit()
    cursor.close()
    print("Database initialized.")
