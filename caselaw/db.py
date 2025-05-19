
# Connect to PostgreSQL
import sqlite3

def get_conn(db="caselaw.db"):
    return sqlite3.connect(db)

def init_db(conn):
    print("Initializing database")
    cursor = conn.cursor()
    # Create table if needed (customize types and columns)
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS legal_case (
            id INTEGER PRIMARY KEY,
            ecli_id TEXT UNIQUE NOT NULL,
            title TEXT,
            celex_id TEXT UNIQUE,
            zaaknummer TEXT UNIQUE,
            uitspraakdatum DATE
        );
        
        CREATE TABLE IF NOT EXISTS law_element (
            id INTEGER PRIMARY KEY,
            -- parent_id INTEGER,
            type TEXT CHECK (type IN ('wet', 'boek', 'deel', 'titeldeel', 'hoofdstuk', 'artikel', 'paragraaf', 'subparagraaf', 'afdeling')),
            bwb_id INTEGER,
            lido_id TEXT UNIQUE,
            jc_id TEXT UNIQUE,
            number TEXT,
            title TEXT,
            alt_title TEXT
            -- FOREIGN KEY (parent_id) REFERENCES law_element(id)
        );

        CREATE TABLE IF NOT EXISTS law_alias (
            id INTEGER PRIMARY KEY,
            law_element_id INTEGER,
            alias TEXT,
            source TEXT,
            FOREIGN KEY (law_element_id) REFERENCES law_element(id)
        );

        CREATE TABLE IF NOT EXISTS case_law (
            id INTEGER PRIMARY KEY,
            case_id INTEGER,
            law_id INTEGER,
            source TEXT CHECK (source IN ('lido-ref', 'lido-linkt', 'custom')),
            jc_id TEXT,
            lido_id TEXT,
            opschrift TEXT,
            FOREIGN KEY (case_id) REFERENCES legal_case(id),
            FOREIGN KEY (law_id) REFERENCES law_element(id)
        );
    """)
    conn.commit()
    cursor.close()
    print("Database initialized.")
