import os
import sqlite3

def create_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Create refs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create aliases table with a foreign key to refs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL,
            ref INTEGER NOT NULL,
            UNIQUE (alias, ref)
            FOREIGN KEY (ref) REFERENCES refs(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX idx_alias ON aliases(alias COLLATE NOCASE);')
    cursor.execute('CREATE INDEX idx_ref ON aliases(ref);')
    
    conn.commit()
    conn.close()
    print(f"Database '{db_name}' created successfully with tables 'aliases' and 'refs'.")

def insert_from_trie_file(file_path, db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(" <- ")
            if len(parts) != 2:
                print("Malformed line: ", line)
                continue  # Skip malformed lines
            
            id_name, aliases = parts
            alias_list = aliases.split("\t")

            
            
            # CREATE TABLE IF NOT EXISTS law_alias (
            #     id INTEGER PRIMARY KEY,
            #     alias TEXT NOT NULL,
            #     bwb_id TEXT NOT NULL,
            #     source TEXT CHECK (source IN ('opschrift', 'bwbidlist')),
            #     UNIQUE (bwb_id, alias COLLATE NOCASE)
            #     -- FOREIGN KEY (law_element_id) REFERENCES law_element(id) ON DELETE CASCADE
            # );
            # CREATE INDEX IF NOT EXISTS idx_law_alias ON law_alias(alias COLLATE NOCASE);
            
            
            # Insert into refs table
            # cursor.execute("INSERT OR IGNORE INTO refs (name) VALUES (?)", (id_name,))
            # cursor.execute("SELECT id FROM refs WHERE name = ?", (id_name,))
            # ref_id = cursor.fetchone()[0]
            
            # Insert into aliases table
            for alias in alias_list:
                cursor.execute("INSERT OR IGNORE INTO law_alias (alias, bwb_id, source) VALUES (?, ?, 'bwbidlist')", (alias, id_name,))
    
    conn.commit()
    conn.close()
    print(f"Data from '{file_path}' inserted successfully into database '{db_name}'.")

def prepare(db_name):
    trie_file = "./data/copied/regeling-aanduiding.trie"

    if not os.path.exists(db_name):
        print("Creating database...")
        # create_database(db_name)
        insert_from_trie_file(trie_file, db_name)
