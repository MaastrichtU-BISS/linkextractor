import os
import sqlite3

from linkextractor.db import get_conn

def insert_from_trie_file(file_path):
    count_bwb = 0
    count_alias = 0

    with get_conn() as conn:
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
                count_bwb += 1
                for alias in alias_list:
                    count_alias+=1
                    cursor.execute("INSERT OR IGNORE INTO law_alias (alias, bwb_id, source) VALUES (?, ?, 'bwbidlist')", (alias, id_name,))
        
        conn.commit()
    
    print(f"From '{file_path}' inserted {count_bwb} bwbs with {count_alias} aliases into database.")

def prepare():
    trie_file = "./data/copied/regeling-aanduiding.trie"
    insert_from_trie_file(trie_file)
