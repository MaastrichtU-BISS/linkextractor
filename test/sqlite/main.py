import re
import sqlite3

# set wrkdir
import os
import pathlib
script_dir = pathlib.Path(__file__).parent.resolve()
os.chdir(script_dir)
# end set wrkdir

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
            alias TEXT NOT NULL UNIQUE,
            ref INTEGER NOT NULL,
            FOREIGN KEY (ref) REFERENCES refs(id) ON DELETE CASCADE
        )
    ''')
    
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
            
            # Insert into refs table
            cursor.execute("INSERT OR IGNORE INTO refs (name) VALUES (?)", (id_name,))
            cursor.execute("SELECT id FROM refs WHERE name = ?", (id_name,))
            ref_id = cursor.fetchone()[0]
            
            # Insert into aliases table
            for alias in alias_list:
                cursor.execute("INSERT OR IGNORE INTO aliases (alias, ref) VALUES (?, ?)", (alias, ref_id))
    
    conn.commit()
    conn.close()
    print(f"Data from '{file_path}' inserted successfully into database '{db_name}'.")

def prepare(db_name):
    trie_file = "../../data/copied/regeling-aanduiding.trie"

    create_database(db_name)
    insert_from_trie_file(trie_file, db_name)

def search(input_text, db_name="database.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Escape any SQL wildcard characters in input
    input_text_escaped = re.sub(r'([_%])', r'\\\1', input_text)

    cursor.execute('''
        SELECT a.alias, r.name FROM aliases a
        JOIN refs r 
            ON (a.ref = r.id)
        WHERE ? LIKE '%' || alias || '%'
        ORDER BY LENGTH(alias) DESC
        LIMIT 10;
    ''', (input_text_escaped,))
    
    results = [row for row in cursor.fetchall()]
    conn.close()
    return results

def match_patterns(text):


    # elementtype <- boek | deel | titeldeel | titel | hoofdstuk | afdeling | paragraaf | subparagraaf | artikel | bijlage | inhoudsopgave | aanwijzing
    # boek <- "boek" | "bk" ?'.'
    # deel <- "deel" | "dl" ?'.' | "onderdeel"
    # titeldeel <- "titeldeel" | "tit" ?'el' 'd' ?'ee' 'l' ?'.'
    # titel <- "titel" | "tit."
    # hoofdstuk <- "hoofdstuk" | "h" ?'f' ?'d' ?'s' ?'t' ?'u' ?'k' ?'.'
    # afdeling <- "afdeling" | "afdeeling" | "afd."
    # paragraaf <- "paragraaf" | "par" ?'a' ?'g' ?'r' ?'aa' ?'f' ?'.'
    # subparagraaf <- "subparagraaf" | "sub" ?'-' "par" ?'a' ?'g' ?'r' ?'aa' ?'f' ?'.'
    # artikel <- ("artikel" ?'en' | "art" ?'t' ?'.') ?(':' ?sp '-')
    # bijlage <- "bijlage" | "bijl" ?'.'
    # inhoudsopgave <- "inh" ('ouds' | '.' | '-') "opg" ?'ave' ?'.'
    # aanwijzing <- "aanwijzing"

    patterns_types = {
        "boek": r"(?:boek|bk\.?)",
        # ...,
        "artikel": r"(?:artikel(?:en)?|artt?\.?)"
    }

    patterns_elementnummer = [
        r"(?:[1-9][.:])?(?:[1-9]?[0-9])?[a-zA-Z](?::?\s*|.)[1-9]*[0-9](?:\s*[a-zA-Z]|\s[a-zA-Z](?=\s))",
        r"[ABCD](?:[12][0-9]|[1-9])(?:\s*[/.,]?\s*(?:[12][0-9]|[1-9]))*(?:\.(?=\bverbinding_elementen_wet\b|\bregeling\b))?",
        r"H[1-9]?[0-9],[1-9]?[0-9]",
        r"[IVXCLDM]+(?![A-Za-z])(?:-[A-Z])?(?:,[1-9]*[0-9]*[a-z])?",
        r"[A-Z]?[ab]?\s*[1-9]?[0-9]?[a-z]?",
        r"[ABCD](?![A-Za-z0-9/.,;])",
        r"[1-9]\.[1-9]?[0-9]:[1-9]?[0-9]",
        r"[1-9]*[0-9]?[a-z] [1-9]"
    ]
    pattern_elementnummer = r"(" + "|".join(patterns_elementnummer) + ")"

    pattern_lidwoorden = r"(?:de|het)"
    
    patterns = [
        # (r"Art(?:\.|ikel|icle) (\d+):(\d+) (.*?)", ["book", "article"]),
        # (r"Art(?:\.|ikel|icle) (\d+) van (.*?)", ["article", "book"]),
        # (r"Art(?:\.|ikel|icle) (\d+) van (.*?)", ["article", "book"]),

        (rf"{patterns_types['artikel']} {pattern_elementnummer} {patterns_types['boek']} {pattern_elementnummer}", )
    ]

    for pattern, keys in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            # return dict(zip(keys, match.groups()))
            # return match.groupdict() # for 
            # return {key: match.group(key) for key in keys} # for named groups
            return {keys[i]: match.group(i + 1) for i in range(len(keys))}
    return None

if __name__ == "__main__":
    db_name = "database.db"
    # prepare(db_name)

    queries = [
        "Art. 7:658 BW",
        "Artikel 7:658 BW",
        "Artikel 658 van boek 7 van het Burgerlijk Wetboek",
        "Burgerlijk Wetboek Boek 7, Artikel 658",
        "Artikel 658 van Boek 7 BW",
        "Art. 7:658 van het Burgerlijk Wetboek", # geeft wel artikel
        "artikel 123 van een Burgerlijk Wetboek" # geen artikel
    ]

    # results_good = []
    # results_bad = []

    for query in queries:
        parts = match_patterns(query)
        print("Parts: ", parts)

        results = search(query, db_name)
        print(f"Query: \"{query}\"")
        print("Results:")
        for result in results:
            print(f"1) {result}")
        print()



