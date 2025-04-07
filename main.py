import re
import sqlite3

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
                print(f" -> {result[0]} ({result[1]})")
    print()
    
def query_exact(query, db_name):
    results = []
    with sqlite3.connect(db_name) as db:
        # print(f"Query: \"{query}\"")

        matches = match_patterns_regex(query)
        for i, match in enumerate(matches):
            print(i, match)
            if not 'book_name' in match['patterns']:
                continue
        
            book_name, book_number = match["patterns"]["book_name"], match["patterns"].get("book_number", None)

            aliases = []
            if book_name is None and book_number is None:
                # article alone is not enough to retrieve books
                pass
            elif book_name is None and book_number is not None:
                # search instances of '%boek {book_number}'
                # shouldnt happen, should always have book name!!!
                aliases = find_matching_aliases(f"boek {book_number}", wildcard=('l'))

            elif book_name is not None and book_number is None:
                # search instances of '{book_name}%' (like BW% will return BW 1, BW 2, ...)
                aliases = find_matching_aliases(book_name, wildcard=('r'))

            elif book_name is not None and book_number is not None:
                # search instances of '{book_name} + {book_number}' (handle cases like Art. 5:123 BW -> Search "BW Boek 5")
                aliases = find_matching_aliases(f"{book_name} boek {book_number}", wildcard=('r'))
                if len(aliases) == 0:
                    aliases = find_matching_aliases(book_name, wildcard=('r'))

            # print(f"{i+1}) Match at character positions {match['span'][0]} to {match['span'][1]} of pattern {match}:")
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
                    # print(f" -> {alias[0]} ({alias[1]})")





            continue
            
            # Find all aliases that are connected to this alias (case-insensitive)
            cursor = db.cursor()
            # cursor.execute("SELECT * FROM aliases WHERE ref IN (SELECT ref FROM aliases WHERE alias = ? COLLATE NOCASE) GROUP BY LOWER(alias)", (match['patterns']['book_name'],))
            cursor.execute('''
                SELECT a1.*
                FROM aliases a1
                JOIN aliases a2 ON a1.ref = a2.ref
                WHERE a2.alias = ? COLLATE NOCASE
                GROUP BY LOWER(a1.alias);
            ''', (match['patterns']['book_name'],))
            # cursor.execute('SELECT DISTINCT * FROM aliases a1 JOIN aliases a2 ON a1.ref = a2.ref WHERE a2.alias = ? COLLATE NOCASE;', (match['patterns']['book_name'],))

            for result in cursor.fetchall():
                print(result)
            
                # results = find_matching_aliases(match['book_name'])
            print(matches)

            print()
    return results

"""
def construct_permutations_given_text(match):
    pt_ws_0 = "\s*" # -> 2
    pt_ws = "\s+" # -> 1
    pts_types = {
        "boek": r"(?:boek|bk\.?)", # -> 3
        # ...,
        "artikel": r"(?:artikel(?:en)?|artt?\.?)" # -> 6
    }
    pt_elementnummer = r"([0-9]+)" # -> fixed
    pt_lidwoorden = r"(?:de|het)?" # -> 2
    pt_opt_tussenvoegsel = rf"(?:van(?:\s+{pt_lidwoorden})?)?{pt_ws_0}" # -> 1*2*2 = 4
    patterns = [
        # "Artikel 5 van het boek 7 van het BW"
        # "Artikel 5 boek 7 BW"
        (rf"{pts_types['artikel']}{pt_ws}{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}{pt_ws}{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}?{pt_ws_0}{pt_matches}", ("article", "book_number", "book_name")),
        # -> 6 * 1 * 1 * 1 * 4 * 3 * 1 * 1 * 1 * 4 * 1 * n = 576*n 

        # "Artikel 61 Wet toezicht trustkantoren 2018"
        (rf"{pts_types['artikel']}{pt_ws}{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("article", "book_name")),
        # -> 6 * 1 * 1 * 1 * 4 * 3*2 * 2 * n = 288*n

        # "Artikel 7:658 van het BW"
        (rf"{pts_types['artikel']}{pt_ws}{pt_elementnummer}:{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("book_number", "article", "book_name")),
        # -> 3 * 1 * 1 * 1 * 4 * 3*2 * 2 * n = 72*n
        
        # "3:2 awb" -> also not parsed on linkeddata
        # (rf"{pt_elementnummer}:{pt_elementnummer}{pt_ws}{pt_opt_tussenvoegsel}{pts_types['boek']}?{pt_ws_0}{pt_matches}", ("book_number", "article", "book_name")),
        
        # "Burgerlijk Wetboek Boek 7, Artikel 658"
        (rf"{pt_matches}(?:{pt_ws}{pts_types['boek']}{pt_ws}{pt_elementnummer})?[,]?{pt_ws_0}{pts_types['artikel']}{pt_ws}{pt_elementnummer}", ("book_name", "book_number", "article")),
        # -> n * (1*3*1*1)*2 *2 *2*6*1*1 = 144*n
    ]

    # Aantal patronen = 576*n + 288*n + 72*n + 144*n = 1080*n, waar n = aantal aliasen
    # Voor BW, waar totaal 41 aliasen over 10 ID's zijn gevonden lijdt dit tot een union van 44280
    pass
"""

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

    queries = [
        "Artikel 3 Wet ter voorkoming van witwassen en financieren van terrorisme (cliëntenonderzoek)",
        "Artikel 61 Wet toezicht trustkantoren 2018 (publicatie bestuurlijke boete)"
    ]

    for i, query in enumerate(queries):
        print(f"{i}) Query: \"{query}\"")

        times = []
        iterations = 10
        for _ in range(iterations):
            time_s = time()
            query_in_text(query, db_name)
            # results = query_exact(query, db_name)
            times.append(time() - time_s)
        print("  Search performance:")
        print(f"  - Iterations:  {iterations}")
        print(f"  - Min time:    {round(min(times), 3)}")
        print(f"  - Mean time:   {round(sum(times) / len(times), 3)}")
        print(f"  - Median time: {round(median(times), 3)}")
        print(f"  - Max time:    {round(max(times), 3)}")
        print()

        if len(results) > 0:
            print("  Results:")
            for i, result in enumerate(results):
                print(f"  - Result {i}: {result}")
            print()
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