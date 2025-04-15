from typing import Union, List
import sqlite3
import re
from src.patterns import PT_ATOMS, PT_REFS, capture, get_patterns

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
