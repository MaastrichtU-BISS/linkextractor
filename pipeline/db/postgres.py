import os
import psycopg2
from dotenv import load_dotenv
import logging

def get_conn(db_url: str | None = None):
    if db_url is None:
        load_dotenv()
        db_url = os.environ["DB_URL"]
    if db_url is None:
        raise Exception("Set the DB_URL environment-variable")
    return psycopg2.connect(db_url, connect_timeout=3)

def init_db(conn):
    logging.debug("Initializing database")
    cursor = conn.cursor()
    # Create table if needed (customize types and columns)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS legal_case (
        id SERIAL PRIMARY KEY,
        ecli_id TEXT UNIQUE NOT NULL,
        title TEXT,
        celex_id TEXT UNIQUE,
        zaaknummer TEXT,
        uitspraakdatum DATE
    );
    CREATE INDEX idx_legal_case_id_ecli ON legal_case (id, ecli_id);

    CREATE TABLE IF NOT EXISTS law_element (
        id SERIAL PRIMARY KEY,
        type TEXT CHECK (type IN ('wet', 'boek', 'deel', 'titeldeel', 'hoofdstuk', 'artikel', 'paragraaf', 'subparagraaf', 'afdeling')),
        bwb_id TEXT,
        bwb_label_id BIGINT,
        lido_id TEXT UNIQUE,
        jc_id TEXT UNIQUE,
        number TEXT,
        title TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_bwb_id ON law_element(bwb_id, bwb_label_id);
    CREATE INDEX IF NOT EXISTS idx_law_element_filter ON law_element (bwb_id, lower(number), type);

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
    CREATE INDEX IF NOT EXISTS idx_caselaw_cl ON case_law (case_id, law_id);
    CREATE INDEX IF NOT EXISTS idx_caselaw_lc ON case_law (law_id, case_id);

    CREATE TABLE IF NOT EXISTS law_alias (
        id SERIAL PRIMARY KEY,
        alias TEXT NOT NULL,
        bwb_id TEXT NOT NULL,
        source TEXT CHECK (source IN ('opschrift', 'bwbidlist'))
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_law_alias_uniq ON law_alias(bwb_id, LOWER(alias));
    CREATE INDEX IF NOT EXISTS idx_law_alias_index ON law_alias(lower(alias));
    """)
    conn.commit()
    cursor.close()
    logging.debug("Database initialized.")
