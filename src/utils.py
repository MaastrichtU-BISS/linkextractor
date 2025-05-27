from typing import Union, List
import sqlite3
import re
from src.db import DB_BACKEND, get_conn
from src.patterns import PT_ATOMS, PT_REFS, capture, get_patterns

def find_aliases_in_text(input_text):
    # performs WHERE ? LIKE column, instead of WHERE column LIKE ?
    with get_conn() as conn:
        cursor = conn.cursor()

        # (wildcard) escaping of input not necessary since the input is the
        # column in the where clause, not the value
        # input_text_escaped = re.sub(r'([_%])', r'\\\1', input_text) 

        if DB_BACKEND == 'sqlite':
            cursor.execute('''
                SELECT id, alias FROM law_alias
                WHERE ? LIKE '%' || alias || '%'
                GROUP BY alias
                LIMIT 50;
            ''', (input_text,))
        elif DB_BACKEND == 'postgres':
            cursor.execute('''
                SELECT id, alias FROM law_alias
                WHERE %s ILIKE '%' || alias || '%'
                GROUP BY alias
                LIMIT 50;
            ''', (input_text,))

        results = []
        for row in cursor.fetchall():
            if re.search(rf"\b{re.escape(row[1])}\b", input_text, flags=re.IGNORECASE):
                results.append(row[1])
        
        conn.close()
        return results

def find_longest_alias_in_substring(input_text):
    # functions similar to find_aliases_in_text, but only does right wildcard and returns single result
    # (used for exact search)
    with get_conn() as conn:
        cursor=conn.cursor()

        if DB_BACKEND == 'sqlite':
            cursor.execute('''
                SELECT alias, bwb_id
                FROM law_alias
                WHERE ? LIKE alias || '%'
                ORDER BY LENGTH(alias) DESC
                LIMIT 1;
            ''', (input_text,))
        elif DB_BACKEND == 'postgres':
            cursor.execute('''
                SELECT alias, bwb_id
                FROM law_alias
                WHERE %s ILIKE alias || '%%'
                ORDER BY LENGTH(alias) DESC
                LIMIT 1;
            ''', (input_text,))

        result = cursor.fetchone()

        return result    

def find_matching_aliases(name, wildcard=None):
    with get_conn() as conn:
        cursor = conn.cursor()
        name_escaped = re.sub(r'([_%])', r'\\\1', name)
        if wildcard is not None:
            if 'l' in wildcard:
                name_escaped = '%'+name_escaped
            if 'r' in wildcard:
                name_escaped = name_escaped+'%'

        if DB_BACKEND == 'sqlite':
            cursor.execute('''
                SELECT s.alias, s.bwb_id, s.length_rank
                FROM (
                    SELECT
                        a.id,
                        a.alias,
                        a.bwb_id,
                        ROW_NUMBER() OVER (PARTITION BY a.bwb_id ORDER BY LENGTH(a.alias) DESC) AS length_rank
                    FROM law_alias a
                    WHERE a.bwb_id IN (
                        SELECT DISTINCT a.bwb_id
                        FROM law_alias a
                        WHERE a.alias LIKE ?
                    )
                ) AS s
                WHERE s.length_rank=1
            ''', (name_escaped,))
        elif DB_BACKEND == 'postgres':
            cursor.execute('''
                WITH ranked_aliases AS (
                    SELECT
                        a.id,
                        a.alias,
                        a.bwb_id,
                        ROW_NUMBER() OVER (PARTITION BY a.bwb_id ORDER BY LENGTH(a.alias) DESC) AS length_rank
                    FROM law_alias a
                    WHERE a.bwb_id IN (
                        SELECT DISTINCT a.bwb_id
                        FROM law_alias a
                        WHERE a.alias ILIKE %s
                    )
                )
                SELECT alias, bwb_id, length_rank
                FROM ranked_aliases
                WHERE length_rank = 1;
            ''', (name_escaped,))
        
        results = [row for row in cursor.fetchall()]
    return results

def get_amount_cases_by_law_filter(result):
    if not 'resource' in result or not 'id' in result['resource'] or \
        not 'fragment' in result or not 'article' in result['fragment']:
        raise Exception("Invalid result")

    with get_conn() as conn:
        cursor = conn.cursor()

        if DB_BACKEND == 'sqlite':
            cursor.execute("""
                SELECT COUNT(DISTINCT c.ecli_id)
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE 
                    l.type = ? AND
                    l.bwb_id = ? AND
                    l.number = ?
            """, ('artikel', result['resource']['id'], result['fragment']['article'],))
        elif DB_BACKEND == 'postgres':
            cursor.execute("""
                SELECT COUNT(DISTINCT c.ecli_id)
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE 
                    l.type = %s AND
                    l.bwb_id = %s AND
                    l.number = %s
            """, ('artikel', result['resource']['id'], result['fragment']['article'],))
        
        amount = cursor.fetchone()
        if amount:
            return amount[0]
        raise Exception("Failed getting amount of cases")

def get_cases_by_law_filter(result):
    if not 'resource' in result or not 'id' in result['resource'] or \
        not 'fragment' in result or not 'article' in result['fragment']:
        raise Exception("Invalid result")

    with get_conn() as conn:
        cursor = conn.cursor()

        if DB_BACKEND == 'sqlite':
            cursor.execute("""
                -- SELECT l.bwb_id, l.type, l.number, c.ecli_id, c.title
                SELECT c.ecli_id
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE 
                    l.type = ? AND
                    l.bwb_id = ? AND
                    l.number = ?
                GROUP BY c.id
                LIMIT 5000
            """, ('artikel', result['resource']['id'], result['fragment']['article'],))
        elif DB_BACKEND == 'postgres':
            cursor.execute("""
                SELECT c.ecli_id
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE 
                    l.type = %s AND
                    l.bwb_id = %s AND
                    l.number = %s
                GROUP BY c.id
                LIMIT 5000
            """, ('artikel', result['resource']['id'], result['fragment']['article'],))
        
        return [row[0] for row in cursor.fetchall()]

def find_laws_from_parts(parts):
    with get_conn() as conn:
        cursor = conn.cursor()
        
        where_clause = " AND ".join([f"l.{parts} = ?" for parts in parts])
        
        if DB_BACKEND == 'sqlite':
            cursor.execute(f"""
                SELECT l.type, l.number, l.bwb_id, l.bwb_label_id, l.title, COUNT(DISTINCT c.ecli_id) as related_cases
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE
                    1=1 AND
                    {where_clause}
                GROUP BY l.bwb_label_id
                LIMIT 5000
            """, tuple(parts.values()))
        elif DB_BACKEND == 'postgres':
            cursor.execute(f"""
                SELECT l.type, l.number, l.bwb_id, l.bwb_label_id, l.title, COUNT(DISTINCT c.ecli_id) as related_cases
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE 
                    1=1 AND
                    {where_clause.replace('?', '%s')}
                GROUP BY l.bwb_label_id, l.type, l.number, l.bwb_id, l.bwb_label_id, l.title
                LIMIT 5000
            """, tuple(parts.values()))

        return [
            {
                'type': row[0],
                'number': row[1],
                'bwb_id': row[2],
                'bwb_label_id': row[3],
                'title': row[4],
                'amount_related_cases': row[5],
            } for row in cursor.fetchall()
        ]

def get_cases_by_bwb_and_label_id(bwb_id, bwb_label_id):
    """
    Returns ECLI-id's related to the bwb and label_id
    """

    assert bwb_id is not None
    assert bwb_label_id is not None

    with get_conn() as conn:
        cursor = conn.cursor()

        if DB_BACKEND == 'sqlite':
            cursor.execute("""
                SELECT c.ecli_id
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE 
                    l.bwb_id = ? AND
                    l.bwb_label_id = ?
                GROUP BY c.id
                LIMIT 5000
            """, (bwb_id, bwb_label_id,))
        elif DB_BACKEND == 'postgres':
            cursor.execute("""
                SELECT c.ecli_id
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE 
                    l.bwb_id = %s AND
                    l.bwb_label_id = %s
                GROUP BY c.id
                LIMIT 5000
            """, (bwb_id, bwb_label_id,))
        
        return [row[0] for row in cursor.fetchall()]

def get_name_of_id(id):
    return None
    # for now, it will simply return the longest alias for the given (bwb)id
    with get_conn() as conn:
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
                WHERE r.name = ?
            )
            WHERE length_rank=1
        ''', (id,))

        result = cursor.fetchone()

        return (result[0], result[3],) # <- ('longest alias string', 'BWB0001234')

def get_aliases_of_ids(id):
    return None
    # return aliases for the given bwbid
    with get_conn() as conn:
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
