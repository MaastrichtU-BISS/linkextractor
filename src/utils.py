from typing import Union, List
import sqlite3
import re

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