import re
import sqlite3
import exrex

# set wrkdir
import os
import pathlib
from typing import List, Union
from statistics import median
from time import time

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
    # performs WHERE ? LIKE column, instead of WHERE column LIKE ?
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # (wildcard) escaping of input not necessary since the input is the
    # column in the where clause, not the value
    # input_text_escaped = re.sub(r'([_%])', r'\\\1', input_text) 

    cursor.execute('''
        SELECT id, alias FROM aliases
        WHERE ? LIKE '%' || alias || '%'
        GROUP BY alias
        LIMIT 50;
    ''', (input_text,))

    results = []
    for row in cursor.fetchall():
        if re.search(rf"\b{re.escape(row[1])}\b", input_text, flags=re.IGNORECASE):
            results.append(row[1])
    
    conn.close()
    return results

def find_longest_alias_in_substring(input_text, db_name="database.db"):
    # functions similar to find_aliases_in_text, but only does right wildcard and returns single result
    # (used for exact search)
    conn=sqlite3.connect(db_name)
    cursor=conn.cursor()

    cursor.execute('''
        SELECT a.alias, r.name
        FROM aliases a
        JOIN refs r ON (a.ref = r.id)
        WHERE ? LIKE alias || '%'
        GROUP BY alias
        ORDER BY LENGTH(alias) DESC
        LIMIT 1;
    ''', (input_text,))

    result = cursor.fetchone()

    return result    

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
    # results = cursor.execute('''
    #     WITH RankedAliases AS (
    #     SELECT a.alias, r.name, a.ref,
    #         MAX(CASE WHEN a.alias LIKE ? THEN 1 ELSE 0 END)
    #         OVER (PARTITION BY a.ref) AS has_match,
    #         ROW_NUMBER() OVER (PARTITION BY a.ref ORDER BY length(a.alias) DESC) AS rn
    #         FROM aliases a
    #         JOIN refs r ON a.ref = r.id
    #     )
    #     SELECT alias, name
    #     FROM RankedAliases
    #     WHERE has_match = 1
    #     AND rn = 1
    #     LIMIT 50;
    # ''', (name_escaped,))

    # # RUN 4 - gpt optimized
    # results = cursor.execute('''
    #     WITH RankedAliases AS (
    #         SELECT a.alias, r.name, a.ref,
    #             MAX(CASE WHEN a.alias LIKE ? THEN 1 ELSE 0 END)
    #             OVER (PARTITION BY a.ref) AS has_match,
    #             ROW_NUMBER() OVER (PARTITION BY a.ref ORDER BY length(a.alias) DESC) AS rn
    #         FROM aliases a
    #         JOIN refs r ON a.ref = r.id
    #         WHERE a.alias LIKE ?  -- Move the filter here for efficiency
    #     )
    #     SELECT alias, name
    #     FROM RankedAliases
    #     WHERE has_match = 1
    #     AND rn = 1
    #     LIMIT 50;
    # ''', (name_escaped,name_escaped,))

    # # RUN 5 - written
    # cursor.execute('''
    #     SELECT a.alias, r.name
    #     FROM aliases a
    #     JOIN refs r ON (a.ref = r.id)
    #     WHERE r.name IN (
    #         SELECT r.name
    #         FROM aliases a
    #         JOIN refs r ON (a.ref = r.id)
    #         WHERE a.alias LIKE ?
    #         GROUP BY r.id
    #         HAVING MIN(r.id)
    #         LIMIT 20
    #     )
    #     GROUP BY r.id
    #     ORDER BY length(a.alias) ASC
    #     LIMIT 20;
    # ''', (name_escaped,))

    # # RUN 6 - written - removed redundant clauses from subquery
    # cursor.execute('''
    #     SELECT a.alias, r.name
    #     FROM aliases a
    #     JOIN refs r ON (a.ref = r.id)
    #     WHERE a.ref IN (
    #         SELECT a.ref
    #         FROM aliases a
    #         WHERE a.alias LIKE ?
    #         GROUP BY a.ref
    #     )
    #     GROUP BY r.id
    #     ORDER BY length(a.alias) ASC
    #     LIMIT 30;
    # ''', (name_escaped,))

    # RUN 7 - written custom
    cursor.execute('''
        SELECT s.alias, r.name, s.ref, s.length_rank
        FROM (
            SELECT
                a.alias,
                a.ref,
                ROW_NUMBER() OVER (PARTITION BY a.ref ORDER BY LENGTH(a.alias) DESC) AS length_rank
            FROM aliases a
            WHERE a.ref IN (
                SELECT DISTINCT a.ref
                FROM aliases a
                WHERE a.alias LIKE ?
            )
        ) AS s
        JOIN refs AS r ON (s.ref = r.id)
        WHERE s.length_rank=1
    ''', (name_escaped,))
    
    results = [row for row in cursor.fetchall()]
    conn.close()
    return results

def get_name_of_id(id, db_name="database.db"):
    # for now, it will simply return the longest alias for the given (bwb)id
    with sqlite3.connect(db_name) as conn:
        cursor=conn.cursor()

        cursor.execute('''
            SELECT alias, ref, length_rank, idname
            FROM (
                SELECT
                    a.alias,
                    a.ref,
                    r.name as idname,
                    ROW_NUMBER() OVER (PARTITION BY a.ref ORDER BY LENGTH(a.alias) DESC) AS length_rank
                FROM aliases a
                JOIN refs r ON (a.ref = r.id)
                WHERE r.name = 'BWBR0002656'
            )
            WHERE length_rank=1
        ''', (id,))

        result = cursor.fetchone()

        return (result[0], result[3],) # <- ('longest alias string', 'BWB0001234')

def get_aliases_of_ids(id, db_name="database.db"):
    # return aliases for the given bwbid
    with sqlite3.connect(db_name) as conn:
        cursor=conn.cursor()

        # cursor.execute(f'''
        #     SELECT DISTINCT alias FROM aliases WHERE ref IN (
        #         SELECT id FROM refs WHERE name IN ({','.join(['?']*len(ids))})
        #     )
        # ''', [id for id in ids])

        cursor.execute(f'''
            SELECT DISTINCT alias FROM aliases WHERE ref IN (
                SELECT id FROM refs WHERE name = ?
            )
        ''', (id,))

        results = [result[0] for result in cursor.fetchall()]

        return results


def match_patterns_regex(text, matches: Union[List[tuple], None] = None):
    """
    If matches is None: assume that the whole of text is the reference searching for
    If matches is not None: assume list of possible matches and search against that
    If matches is not None but empty: attempted to find matches but no matches to find against so return []
    """
    if matches is not None and len(matches) == 0:
        return []

    pt_ws_0 = "\s*"
    pt_ws = "\s+"
    pts_types = {
        "boek": r"(?:boek|bk\.?)",
        # ...,
        "artikel": r"(?:artikel(?:en)?|artt?\.?)"
    }

    # from waxeye grammar:
    # pts_elementnummer = [
    #     r"(?:[1-9][.:])?(?:[1-9]?[0-9])?[a-zA-Z](?::?\s*|.)[1-9]*[0-9](?:\s*[a-zA-Z]|\s[a-zA-Z](?=\s))",
    #     r"[ABCD](?:[12][0-9]|[1-9])(?:\s*[/.,]?\s*(?:[12][0-9]|[1-9]))*(?:\.(?=\bverbinding_elementen_wet\b|\bregeling\b))?",
    #     r"H[1-9]?[0-9],[1-9]?[0-9]",
    #     r"[IVXCLDM]+(?![A-Za-z])(?:-[A-Z])?(?:,[1-9]*[0-9]*[a-z])?",
    #     r"[A-Z]?[ab]?\s*[1-9]?[0-9]?[a-z]?",
    #     r"[ABCD](?![A-Za-z0-9/.,;])",
    #     r"[1-9]\.[1-9]?[0-9]:[1-9]?[0-9]",
    #     r"[1-9]*[0-9]?[a-z] [1-9]"
    # ]
    # pt_elementnummer = r"(" + "|".join(pts_elementnummer) + ")"
    pt_nr_boek = r"([0-9]+)"
    pt_nr_artikel = r"(\d+(?:\.\d+)?[a-zA-Z]?(?:-[a-zA-Z0-9]+)?)" # matches: 1, 1.12, 1.2a, 1b, 1b-c, 1-2

    pt_lidwoorden = r"(?:de|het)?"
    pt_opt_tussenvoegsel = rf"(?:van(?:\s+{pt_lidwoorden})?)?{pt_ws_0}"

    if matches is not None:
        pt_matches = "(" + "|".join(re.escape(match) for match in matches) + ")"
    else:
        pt_matches = r"(.+?)"
    
    patterns = [
        # "Artikel 5 van het boek 7 van het BW"
        # "Artikel 5 boek 7 BW"
        (
            rf"{pts_types['artikel']}{pt_ws}{pt_nr_artikel}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}{pt_ws}{pt_nr_boek}{pt_ws}{pt_opt_tussenvoegsel}?{pt_ws_0}{pt_matches}",
            ("article", "book_number", "book_name",)
        ),

        # "Artikel 61 Wet toezicht trustkantoren 2018"
        (
            rf"{pts_types['artikel']}{pt_ws}{pt_nr_artikel}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}",
            ("article", "book_name",)
        ),

        # "Artikel 7:658 van het BW"
        (
            rf"{pts_types['artikel']}{pt_ws}{pt_nr_boek}:{pt_nr_artikel}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}",
            ("book_number", "article", "book_name",)
        ),
        
        # "Burgerlijk Wetboek Boek 7, Artikel 658"
        (
            rf"{pt_matches}(?:{pt_ws}{pts_types['boek']}{pt_ws}{pt_nr_boek})?[,]?\s*{pts_types['artikel']}{pt_ws}{pt_nr_artikel}",
            ("book_name", "book_number", "article",)
        ),
        
        # "3:2 awb" -> also not parsed on linkeddata
        # TODO: make this only match if not other match found???
        (rf"{pt_nr_boek}:{pt_nr_artikel}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("book_number", "article", "book_name")),
    ]
    
    results = []

    for pattern, keys in patterns:
        if matches is None:
            # if matches not passed, assume matching pattern from start to end of line
            pattern = rf"^\s*{pattern}\s*$"
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            results.append({
                "span": match.span(),
                "patterns": {keys[i]: match.group(i + 1) for i in range(len(keys))}
            })
    
    return results

def query_in_text(query, db_name):
    print(f"Query: \"{query}\"")

    aliases = find_aliases_in_text(query, db_name)

    print("Aliases:")
    for i, alias in enumerate(aliases):
        print(f"{i+1}) {alias}")
    
    matches = match_patterns_regex(query, aliases)
    
    end_results = []

    if len(matches) == 0:
        if len(aliases) == 0:
            print("Oops! We didn't find any pattern matches nor did we find aliases. Skipping!")
            return
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
                end_results.append(result)
                print(f" -> {result[0]} ({result[1]})")
    print()
    return end_results
    
def query_exact(query: str, db_name="database.db"):
    query = query.strip()
    results = []

    matches = match_patterns_regex(query)
    if len(matches) == 0:
        aliases = find_matching_aliases(query, wildcard=('l', 'r'))
        if len(aliases) == 0:
            found = find_longest_alias_in_substring(query)
            aliases = [found] if found is not None else []
        
        for alias in aliases:
            result = {
                'resource': {
                    'name': alias[0],
                    'id': alias[1]
                }
            }
    else:
        for i, match in enumerate(matches):
            if not 'book_name' in match['patterns']:
                continue
        
            book_name, book_number = match["patterns"]["book_name"], match["patterns"].get("book_number", None)

            aliases = []
            if book_name is None:
                if book_number is None:
                    # article alone is (currently) not enough to retrieve books
                    pass
                elif book_name is None and book_number is not None:
                    # search instances of '%boek {book_number}'
                    # shouldnt happen, should always have book name!!!
                    aliases = find_matching_aliases(f"boek {book_number}", wildcard=('l'))

            elif book_name is not None:
                if book_number is None:
                    # search instances of '{book_name}%' (like BW% will return BW 1, BW 2, ...)
                    aliases = find_matching_aliases(book_name, wildcard=('r'))

                elif book_number is not None:
                    # search instances of '{book_name} + {book_number}' (handle cases like Art. 5:123 BW -> Search "BW Boek 5")
                    aliases = find_matching_aliases(f"{book_name} boek {book_number}", wildcard=('r'))
                    if len(aliases) == 0:
                        # search without 'boek {nr}' suffix
                        aliases = find_matching_aliases(book_name, wildcard=('r'))
                
                if len(aliases) == 0:
                    # if above both didnt lead to results, perform substring match
                    # this (temporarily) fixes 
                    found = find_longest_alias_in_substring(book_name)
                    aliases = [found] if found is not None else aliases

            if len(aliases) == 0:
                # print(" -> NO RESULTS (shouldn't happend)")
                pass
            else:
                for alias in aliases:
                    result = {
                        'resource': {
                            'name': alias[0],
                            'id': alias[1]
                        }
                    }
                    if 'article' in match['patterns']:
                        result['article'] = match['patterns']['article']
                    if 'book_number' in match['patterns']:
                        result['book'] = match['patterns']['book_number']
                    results.append(result)

    return results

"""
def construct_permutations_given_text_old(matches, number):
    pt_ws_0 = "\s*" # -> 2
    pt_ws = "\s+" # -> 1
    pts_types = {
        "boek": r"(?:boek|bk\.?)", # -> 3
        # ...,
        "artikel": r"(?:artikel(?:en)?|artt?\.?)" # -> 6
    }
    pt_lidwoorden = r"(?:de|het)?" # -> 2
    pt_opt_tussenvoegsel = rf"(?:van(?:\s+{pt_lidwoorden})?)?{pt_ws_0}" # -> 1*2*2 = 4

    pt_matches = "(" + "|".join(re.escape(match) for match in matches) + ")" # -> n (len(matches))

    pt_elementnummer = r"([0-9]+)" # -> 10
    
    pt_nr_boek = r"([0-9]+)" # -> 
    if numbers['book']:
        pt_nr_boek = "(" + "|".join(re.escape(n) for n in numbers['book']) + ")" # <- typically 1
    
    pt_nr_artikel = r"(\d+(?:\.\d+)?[a-zA-Z]?(?:-[a-zA-Z0-9]+)?)" # matches: 1, 1.12, 1.2a, 1b, 1b-c, 1-2
    if numbers['article']:
        pt_nr_artikel = "(" + "|".join(re.escape(n) for n in numbers['article']) + ")" # <- typically 1

    patterns = [
        # "Artikel 5 van het boek 7 van het BW"
        # "Artikel 5 boek 7 BW"
        (rf"{pts_types['artikel']}{pt_ws}{pt_nr_artikel}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}{pt_ws}{pt_nr_boek}{pt_ws}{pt_opt_tussenvoegsel}?{pt_ws_0}{pt_matches}", ("article", "book_number", "book_name")),
        # -> 6 * 1 * 1 * 1 * 4 * 3 * 1 * 1 * 1 * 4 * 1 * n = 576*n 

        # "Artikel 61 Wet toezicht trustkantoren 2018"
        (rf"{pts_types['artikel']}{pt_ws}{pt_nr_artikel}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("article", "book_name")),
        # -> 6 * 1 * 1 * 1 * 4 * 3*2 * 2 * n = 288*n

        # "Artikel 7:658 van het BW"
        (rf"{pts_types['artikel']}{pt_ws}{pt_nr_boek}:{pt_nr_artikel}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("book_number", "article", "book_name")),
        # -> 3 * 1 * 1 * 1 * 4 * 3*2 * 2 * n = 72*n
        
        # "3:2 awb" -> also not parsed on linkeddata
        # (rf"{pt_elementnummer}:{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("book_number", "article", "book_name")),
        
        # "Burgerlijk Wetboek Boek 7, Artikel 658"
        (rf"{pt_matches}(?:{pt_ws}{pts_types['boek']}{pt_ws}{pt_nr_boek})?[,]?{pt_ws_0}{pts_types['artikel']}{pt_ws}{pt_nr_artikel}", ("book_name", "book_number", "article")),
        # -> n * (1*3*1*1)*2 *2 *2*6*1*1 = 144*n
    ]

    total_regex = "(?:" + ")|(".join([p[0] for p in patterns]) + ")"

    return total_regex

    # Aantal patronen = 576*n + 288*n + 72*n + 144*n = 1080*n, waar n = aantal aliasen
    # Voor BW, waar totaal 41 aliasen over 10 ID's zijn gevonden lijdt dit tot een union van 44280
    pass
"""

# """
def construct_permutations_given_text(matches, numbers):
    pt_ws_0 = "[ ]?" # -> 2
    pt_ws = "[ ]" # -> 1
    pts_types = {
        "boek": r"(?:boek|bk\.?)", # -> 3
        # ...,
        "artikel": r"(?:artikel(?:en)?|artt?\.?)" # -> 6
    }
    pt_lidwoorden = r"(?:de|het)" # -> 2
    pt_opt_tussenvoegsel = rf"(?:{pt_ws}van(?:{pt_ws}{pt_lidwoorden})?)?" # -> 1*2*2 = 4

    pt_matches = "(" + "|".join(re.escape(match) for match in matches) + ")" # -> n (len(matches))

    pt_elementnummer = r"([0-9]+)" # -> 10
    
    pt_nr_boek = r"([0-9]+)" # -> 
    if numbers['book']:
        pt_nr_boek = "(" + "|".join(re.escape(n) for n in numbers['book']) + ")" # <- typically 1
    
    pt_nr_artikel = r"(\d+(?:\.\d+)?[a-zA-Z]?(?:-[a-zA-Z0-9]+)?)" # matches: 1, 1.12, 1.2a, 1b, 1b-c, 1-2
    if numbers['article']:
        pt_nr_artikel = "(" + "|".join(re.escape(n) for n in numbers['article']) + ")" # <- typically 1

    patterns = [
        # "Artikel 5 van het boek 7 van het BW"
        # "Artikel 5 boek 7 BW"
        (rf"{pts_types['artikel']}{pt_ws}{pt_nr_artikel}{pt_opt_tussenvoegsel}{pt_ws}{pts_types['boek']}{pt_ws}{pt_nr_boek}{pt_opt_tussenvoegsel}{pt_ws}{pt_matches}", ("article", "book_number", "book_name")),
        # -> 6 * 1 * 1 * 1 * 4 * 3 * 1 * 1 * 1 * 4 * 1 * n = 576*n 

        # "Artikel 61 Wet toezicht trustkantoren 2018"
        (rf"{pts_types['artikel']}{pt_ws}{pt_nr_artikel}{pt_opt_tussenvoegsel}{pt_ws}(?:{pts_types['boek']}{pt_ws})?{pt_matches}", ("article", "book_name")),
        # -> 6 * 1 * 1 * 1 * 4 * 3*2 * 2 * n = 288*n

        # "Artikel 7:658 van het BW"
        (rf"{pts_types['artikel']}{pt_ws}{pt_nr_boek}:{pt_nr_artikel}{pt_opt_tussenvoegsel}{pt_ws}(?:{pts_types['boek']}{pt_ws})?{pt_matches}", ("book_number", "article", "book_name")),
        # -> 3 * 1 * 1 * 1 * 4 * 3*2 * 2 * n = 72*n
        
        # "3:2 awb" -> also not parsed on linkeddata
        # (rf"{pt_elementnummer}:{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("book_number", "article", "book_name")),
        
        # "Burgerlijk Wetboek Boek 7, Artikel 658"
        (rf"{pt_matches}(?:{pt_ws}{pts_types['boek']}{pt_ws}{pt_nr_boek})?(?:[,]{pt_ws_0}|{pt_ws}){pts_types['artikel']}{pt_ws}{pt_nr_artikel}", ("book_name", "book_number", "article")),
        # -> n * (1*3*1*1)*2 *2 *2*6*1*1 = 144*n
    ]

    total_regex = "(?:" + ")|(".join([p[0] for p in patterns]) + ")"

    return total_regex

    # Aantal patronen = 576*n + 288*n + 72*n + 144*n = 1080*n, waar n = aantal aliasen
    # Voor BW, waar totaal 41 aliasen over 10 ID's zijn gevonden lijdt dit tot een union van 44280
    pass
# """

"""
def find_ambiguous_aliases():
    dic = {}
    with open("./data/copied/regeling-aanduiding.trie", 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(" <- ")
            if len(parts) != 2:
                continue
            id_name, aliases = parts
            alias_list = aliases.split("\t")
            for alias in alias_list:
                if alias not in dic:
                    dic[alias] = [id_name]
                elif not id_name in dic[alias]:
                    dic[alias].append(id_name)
    ambiguous = {k: v for k, v in dic.items() if len(v) > 1}
    ambiguous = dict(sorted(ambiguous.items(), key=lambda item: -len(item[1])))
    for amb_alias, amb_ids in ambiguous.items():
        print(f"Ambiguous alias: '{amb_alias}', belongs to {len(amb_ids)} ids: {', '.join(amb_ids)}")
    exit()
"""

if __name__ == "__main__":
    db_name = "database.db"
    prepare(db_name)

    ## START GET PERMUTATIONS 
    query = "Art 5:1 BW"

    exact_matches = query_exact(query, db_name)

    exact_aliases = []
    numbers = {
        'book': [],
        'article': [],
    }

    for exact_match in exact_matches:
        if exact_match['article'] and exact_match['article'] not in numbers['article']:
            numbers['article'].append(exact_match['article'])
        if exact_match['book'] and exact_match['book'] not in numbers['book']:
            numbers['book'].append(exact_match['book'])
        
        aliases = get_aliases_of_ids(exact_match['resource']['id'])
        for alias in aliases:
            exact_aliases.append(alias)

    large_regex = construct_permutations_given_text(exact_aliases, numbers)
    print(large_regex)

    # writings = list(exrex.generate(large_regex, 1))
    # for (i, writing) in enumerate(writings):
    #     print(i, writing)

    print("AMOUNT", exrex.count(large_regex, 2))

    i = 1
    for writing in exrex.generate(large_regex, 2):
        # print(writing)
        print(i, writing)
        i+=1

        if i>10000:
            break

    # print(regex)

    exit()
    ## END GET PERM.

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

        "Artikel 4:8 Algemene wet bestuursrecht (hoor en wederhoor)", # <-- article is "4:8" ? but could also be interpreted as book 4 article 8
        "4:8 Awb",

        "Verordening (EG) nr. 1618/1999",

        "Artikel 7.4 WHW",
        "Artikel 7.12B WHW",
        "Artikel 7.28 WHW",
        "Artikel 7.30b WHW",
        "Artikel 7.57H WHW",
        "Artikel 7.61 WHW",
        "Artikel 9.19 WHW",
        "5:1 BW",
        "art. 1 Wet gelijke behandeling op grond van handicap of chronische ziekte",
    ]

    # TODO:
    # 1 and 2: longest substring search
    # 3: implement rule for 5:1 BW
    # 4: extend article patterns to include dots and have alphanumerical suffixes
    queries = [
        "Artikel 3 Wet ter voorkoming van witwassen en financieren van terrorisme (cliëntenonderzoek)",
        "Artikel 61 Wet toezicht trustkantoren 2018 (publicatie bestuurlijke boete)",
        "5:1 BW",
        "Artikel 7.12B WHW",
        "Artikel 4:8 Algemene wet bestuursrecht (hoor en wederhoor)",
        "Artikel 4:8 AWB"
    ]

    for i, query in enumerate(queries):
        print(f"{i}) Query: \"{query}\"")

        times = []
        iterations = 10
        for _ in range(iterations):
            time_s = time()
            # results = query_in_text(query, db_name)
            results = query_exact(query, db_name)
            times.append(time() - time_s)
        print("  Search performance:")
        print(f"  - Iterations:  {iterations}")
        print(f"  - Min time:    {round(min(times), 5)}")
        print(f"  - Mean time:   {round(sum(times) / len(times), 5)}")
        print(f"  - Median time: {round(median(times), 5)}")
        print(f"  - Max time:    {round(max(times), 5)}")
        print()

        if len(results) > 0:
            print("  Results:")
            for i, result in enumerate(results):
                print(f"  - Result {i}: {result}")
            print()
        else:
            print("  No results.")
        print()
        
        # break

    # a = find_matching_aliases(f"Algemene wet bestuursrecht", wildcard=('r'))
    
"""
TODO improvements:
 - ensure that single matches are not part of words (such as "Burgerlijk Wetboek" matching "LI" -> Liftenbesluit, etc.)
   [-] ensure that matches in find_aliases_in_text are not part or words
   - ensure that when finding relevant wildcards in find_matching_aliases, it is either that or has a space
 [-] for found matched aliases, search its id and return the longest alias given that id
 - simpler implementation for only search
 [-] nice output, with article if included (json)

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