import re
import sqlite3

# set wrkdir
import os
import pathlib
from typing import List
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
            alias TEXT NOT NULL,
            ref INTEGER NOT NULL,
            UNIQUE (alias, ref)
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
    trie_file = "./data/copied/regeling-aanduiding.trie"

    if not os.path.exists(db_name):
        print("Creating database...")
        create_database(db_name)
        insert_from_trie_file(trie_file, db_name)

def find_aliases_in_text(input_text, db_name="database.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # input_text_escaped = re.sub(r'([_%])', r'\\\1', input_text)

    cursor.execute('''
        SELECT id, alias FROM aliases
        WHERE ? LIKE '%' || alias || '%'
        GROUP BY alias
        ORDER BY LENGTH(alias) DESC
        LIMIT 50;
    ''', (input_text,))

    results = []
    for row in cursor.fetchall():
        if re.search(rf"\b{re.escape(row[1])}\b", input_text):
            results.append(row[1])
    
    conn.close()
    return results

def find_matching_aliases(name, wildcard=None, db_name="database.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    name_escaped = re.sub(r'([_%])', r'\\\1', name)
    if wildcard is not None:
        if 'l' in wildcard:
            name_escaped = '%'+name_escaped
        if 'r' in wildcard:
            name_escaped = name_escaped+'%'
    
    ## RUN 1 - written
    # cursor.execute('''
    #     SELECT a.alias, r.name
    #     FROM aliases a
    #     JOIN refs r ON (a.ref = r.id)
    #     WHERE a.alias LIKE ?
    #     GROUP BY r.id
    #     HAVING MIN(r.id)
    #     LIMIT 20;
    # ''', (name_escaped,))
    # results = []
    # for row in cursor.fetchall():

    #     res2 = cursor.execute('''
    #         SELECT a.alias, r.name
    #         FROM aliases a
    #         JOIN refs r ON (a.ref = r.id)
    #         WHERE r.name = ?
    #         ORDER BY length(a.alias) DESC
    #         LIMIT 1;
    #     ''', (row[1],))

    #     results.append(res2.fetchone())

    ## RUN 2 - gpt without window
    # results = cursor.execute('''
    #     WITH matched_refs AS (
    #     SELECT DISTINCT ref
    #     FROM aliases
    #     WHERE alias LIKE 'awb'
    #     ),
    #     longest_alias AS (
    #     SELECT a.ref, a.alias
    #     FROM aliases a
    #     JOIN (
    #         SELECT ref, MAX(length(alias)) AS max_len
    #         FROM aliases
    #         GROUP BY ref
    #     ) m ON a.ref = m.ref AND length(a.alias) = m.max_len
    #     )
    #     SELECT la.alias, r.name
    #     FROM longest_alias la
    #     JOIN refs r ON r.id = la.ref
    #     WHERE la.ref IN (SELECT ref FROM matched_refs)
    #     LIMIT 30;
    # ''', (name_escaped,))

    # RUN 3 - gpt with window
    results = cursor.execute('''
        WITH RankedAliases AS (
        SELECT a.alias, r.name, a.ref,
            MAX(CASE WHEN a.alias LIKE ? THEN 1 ELSE 0 END)
            OVER (PARTITION BY a.ref) AS has_match,
            ROW_NUMBER() OVER (PARTITION BY a.ref ORDER BY length(a.alias) DESC) AS rn
            FROM aliases a
            JOIN refs r ON a.ref = r.id
        )
        SELECT alias, name
        FROM RankedAliases
        WHERE has_match = 1
        AND rn = 1
        LIMIT 50;
    ''', (name_escaped,))

    results = [row for row in cursor.fetchall()]
    conn.close()
    return results



def match_patterns_regex(text, matches: List[tuple]):
    if False:
        pass
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

    pt_ws_0 = "\s*"
    pt_ws = "\s+"
    pts_types = {
        "boek": r"(?:boek|bk\.?)",
        # ...,
        "artikel": r"(?:artikel(?:en)?|artt?\.?)"
    }

    pt_elementnummer = [
        r"(?:[1-9][.:])?(?:[1-9]?[0-9])?[a-zA-Z](?::?\s*|.)[1-9]*[0-9](?:\s*[a-zA-Z]|\s[a-zA-Z](?=\s))",
        r"[ABCD](?:[12][0-9]|[1-9])(?:\s*[/.,]?\s*(?:[12][0-9]|[1-9]))*(?:\.(?=\bverbinding_elementen_wet\b|\bregeling\b))?",
        r"H[1-9]?[0-9],[1-9]?[0-9]",
        r"[IVXCLDM]+(?![A-Za-z])(?:-[A-Z])?(?:,[1-9]*[0-9]*[a-z])?",
        r"[A-Z]?[ab]?\s*[1-9]?[0-9]?[a-z]?",
        r"[ABCD](?![A-Za-z0-9/.,;])",
        r"[1-9]\.[1-9]?[0-9]:[1-9]?[0-9]",
        r"[1-9]*[0-9]?[a-z] [1-9]"
    ]
    # pt_elementnummer = r"(" + "|".join(patterns_elementnummer) + ")"
    pt_elementnummer = r"([0-9]+)"

    pt_lidwoorden = r"(?:de|het)?"
    pt_opt_tussenvoegsel = rf"(?:van(?:\s+{pt_lidwoorden})?)?{pt_ws_0}"

    pt_matches = "(" + "|".join(re.escape(match) for match in matches) + ")"
    
    patterns = [
        # "Artikel 5 van het boek 7 van het BW"
        # "Artikel 5 boek 7 BW"
        (rf"{pts_types['artikel']}{pt_ws}{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}{pt_ws}{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}?{pt_ws_0}{pt_matches}", ("article", "book_number", "book_name")),

        # "Artikel 61 Wet toezicht trustkantoren 2018"
        (rf"{pts_types['artikel']}{pt_ws}{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("article", "book_name")),

        # "Artikel 7:658 van het BW"
        (rf"{pts_types['artikel']}{pt_ws}{pt_elementnummer}:{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("book_number", "article", "book_name")),
        
        # "3:2 awb"
        # (rf"{pt_elementnummer}:{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("book_number", "article", "book_name")),
        
        # "Burgerlijk Wetboek Boek 7, Artikel 658"
        (rf"{pt_matches}(?:{pt_ws}{pts_types['boek']}{pt_ws}{pt_elementnummer})?[,]?\s*{pts_types['artikel']}{pt_ws}{pt_elementnummer}", ("book_name", "book_number", "article")),
        
        (rf"{pt_matches}(?:{pt_ws}{pts_types['boek']}{pt_ws}{pt_elementnummer})?[,]?\s*{pts_types['artikel']}{pt_ws}{pt_elementnummer}", ("book_name", "book_number", "article")),
    ]
    
    results = []

    for pattern, keys in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            results.append({
                "span": match.span(),
                "patterns": {keys[i]: match.group(i + 1) for i in range(len(keys))}
            })
    
    return results

if __name__ == "__main__":
    db_name = "database.db"
    prepare(db_name)

    queries = [
        "Art. 7:658 BW",
        "Artikel 7:658 BW",
        "Artikel 7:658 Burgerlijk Wetboek", # geen resultaat op linkeddata
        "Artikel 7:658 van het BW", # geeft resultaat
        "Artikel 7:658 van het BW boek 7", # geeft geen resultaat maar wel geldig
        "Artikel 658 van boek 7 van het Burgerlijk Wetboek",
        "Artikel 658 van het boek 7 van het Burgerlijk Wetboek",
        "Burgerlijk Wetboek Boek 7, Artikel 658",
        "Burgerlijk Wetboek, Artikel 658",
        "Artikel 658 van Boek 7 BW",
        "Art. 7:658 van het Burgerlijk Wetboek",
        "Ik heb dat gelezen in art. 7:658 BW of in BW, artikel 5.",
        "Burgerlijk Wetboek",

        # van xslx ->
        "Artikel 1:75 Wet op het financieel toezicht",
        "1:75 Wft",

        "Artikel 3 Wet ter voorkoming van witwassen en financieren van terrorisme (cliëntenonderzoek)",
        "Artikel 16 Wet ter voorkoming van witwassen en financieren van terrorisme (FIU-meldplicht)",
        "Artikel 61 Wet toezicht trustkantoren 2018 (publicatie bestuurlijke boete)",
        "Artikel 3:2 Algemene wet bestuursrecht (zorgvuldigheidsbeginsel)",
        "Artikel 3:2 Algemene wet bestuursrecht (zorgvuldigheidsbeginsel) + DNB OR AFM",
        "3:2 awb",

        "Artikel 4:8 Algemene wet bestuursrecht (hoor en wederhoor)",
        "4:8 Awb",

        "Verordening (EG) nr. 1618/1999",
    ]

    for query in queries:
        aliases = find_aliases_in_text(query, db_name)
        print(f"Query: \"{query}\"")

        print("Results:")
        for i, alias in enumerate(aliases):
            print(f"{i+1}) {alias}")

        matches = match_patterns_regex(query, aliases)
        if len(matches) == 0:
            if len(aliases) == 0:
                print("Oops! We didn't find any pattern matches nor did we find aliases. Skipping!")
                continue
            else:
                print("Hmm. We didn't find any pattern matches but we did we find aliases! We'll continue with all of those.")
                matches = []
                for alias in aliases:
                    span = (None, None)
                    span_search = query.find(alias)
                    if span_search > -1:
                        span = (span_search, span_search+len(alias),)
                    matches.append({
                        "span": span,
                        "patterns": {
                            "book_name": alias,
                            "book_number": None,
                            "article": None
                        }
                    })

        print("Matches:")
        for i, match in enumerate(matches):
            match["patterns"]["book_name"]
            
            book_name, book_number = match["patterns"]["book_name"], match["patterns"].get("book_number", None)

            results = []
            if book_name is None and book_number is None:
                # article alone is not enough to retrieve books
                pass
            elif book_name is None and book_number is not None:
                # search instances of '%boek {book_number}'
                # shouldnt happen, should always have book name!!!
                results = find_matching_aliases(f"boek {book_number}", wildcard=('l'))

            elif book_name is not None and book_number is None:
                # search instances of '{book_name}%' (like BW% will return BW 1, BW 2, ...)
                results = find_matching_aliases(book_name, wildcard=('r'))

            elif book_name is not None and book_number is not None:
                # search instances of '{book_name} + {book_number}' (handle cases like Art. 5:123 BW -> Search "BW Boek 5")
                results = find_matching_aliases(f"{book_name} boek {book_number}", wildcard=('r'))
                if len(results) == 0:
                    results = find_matching_aliases(book_name, wildcard=('r'))

            print(f"{i+1}) Match at character positions {match['span'][0]} to {match['span'][1]} of pattern {match}:")
            if len(results) == 0:
                print(" -> NO RESULTS (shouldn't happend)")
            else:
                for result in results:
                    print(f" -> {result[0]} ({result[1]})")

        print()
    
    # a = find_matching_aliases(f"Algemene wet bestuursrecht", wildcard=('r'))
    
"""
TODO improvements:
 - ensure that single matches are not part of words (such as "Burgerlijk Wetboek" matching "LI" -> Liftenbesluit, etc.)
   [-] ensure that matches in find_aliases_in_text are not part or words
   - ensure that when finding relevant wildcards in find_matching_aliases, it is either that or has a space
 [-] for found matched aliases, search its id and return the longest alias given that id
 - nice output, with article if included (json)
 - performance, keep dataabse connection open

 Edge cases
 - awb:
    -> on linkeddata, only Algemene Wet Bestuursrecht
    -> In here, there seem many aliases of AWB with longer full names
 - burgelijk wetboek
    -> returns much to many offsets
 - bw, artikel 5
    -> should return all of BW with suffixes (maybe it does but restricted by results)
"""