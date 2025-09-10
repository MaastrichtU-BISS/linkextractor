import logging
from typing import Union, List
import sqlite3
import re
from src.db import DB_BACKEND, get_conn
from src.patterns import PT_ATOMS, PT_REFS, capture, get_patterns
from src.types import LinkList

def find_aliases_in_text(input_text):
    # performs WHERE ? LIKE column, instead of WHERE column LIKE ?
    with get_conn() as conn:
        cursor = conn.cursor()

        # (wildcard) escaping of input not necessary since the input is the
        # column in the where clause, not the value
        # input_text_escaped = re.sub(r'([_%])', r'\\\1', input_text)

        if DB_BACKEND == 'sqlite':
            cursor.execute('''
                SELECT alias FROM law_alias
                WHERE ? LIKE '%' || alias || '%'
                GROUP BY alias
                LIMIT 50;
            ''', (input_text,))
        elif DB_BACKEND == 'postgres':
            cursor.execute('''
                SELECT DISTINCT alias FROM law_alias
                WHERE %s ILIKE '%%' || alias || '%%'
                LIMIT 50;
            ''', (input_text,))

        results = []
        for (alias,) in cursor.fetchall():
            if re.search(rf"\b{re.escape(alias)}\b", input_text, flags=re.IGNORECASE):
                results.append(alias)

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

        row = cursor.fetchone()
        if not row:
            return None

        result = {
            'alias': row[0],
            'bwb_id': row[1]
        }

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

        results = [{
            'alias': row[0],
            'bwb_id': row[1]
        } for row in cursor.fetchall()]
    return results

def get_amount_cases_by_law_filter(result):
    return None
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
    return None
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

# find_laws_from_parts
# returns all laws from the database that satisfy the parts passed
# parts contain information from regex pattern matching
def find_laws_from_parts(parts) -> LinkList:
    with get_conn() as conn:
        cursor = conn.cursor()

        where_clause = []
        where_values = []
        if 'bwb_id' in parts:
            where_clause.append('l.bwb_id = ?')
            where_values.append(parts['bwb_id'])
        if 'article' in parts:
            where_clause.append('l.type = ?')
            where_values.append('artikel')
            where_clause.append('lower(l.number) = lower(?)')
            where_values.append(parts['article'])

        where_clause = " AND ".join(where_clause)

        if DB_BACKEND == 'sqlite':
            cursor.execute(f"""
                SELECT l.type, l.number, l.bwb_id, l.bwb_label_id, l.title
                FROM law_element l
                WHERE
                    1=1 AND
                    {where_clause}
                GROUP BY l.type, l.number, l.bwb_id, l.bwb_label_id, l.title
                LIMIT 5000
            """, where_values)
        elif DB_BACKEND == 'postgres':
            cursor.execute(f"""
                SELECT l.type, l.number, l.bwb_id, l.bwb_label_id, l.title
                FROM law_element l
                WHERE
                    1=1 AND
                    {where_clause.replace('?', '%s')}
                GROUP BY l.type, l.number, l.bwb_id, l.bwb_label_id, l.title
                LIMIT 5000
            """, where_values)

        # for row in cursor.fetchall():
        #     logging.debug(row)

        laws: LinkList = []

        for row in cursor.fetchall():

            new_law = {
                'resource': {
                    'name': row[4],
                    'bwb_id': row[2],
                    'bwb_label_id': row[3],
                },
                'fragment': {}
            }

            new_law['fragment'][row[0]] = row[1]
        
        return laws
    
def find_law(alias, fragments):
    assert DB_BACKEND=="postgres", "postgres is needed for this function"

    assert len(alias.strip()) == 0, "alias should not be empty"
    assert len(fragments) == 0, "list of fragments should not be empty"
    
    # order fragments based on specificity/narrowness
    type_order = ['wet', 'boek', 'deel', 'titeldeel', 'hoofdstuk', 'artikel',
        'paragraaf', 'subparagraaf', 'afdeling']
    order_map = {law_type: index for index, law_type in enumerate(type_order)}
    fragments = sorted(fragments, key=lambda frag: order_map[frag[0]])

    # determine most narrow fragment
    narrow_fragment_type, narrow_fragment_number = fragments[-1]

    with get_conn() as conn:
        cursor = conn.cursor()

        # fragment_params = [item for sublist in fragments for item in sublist]
        params = (
            alias.lower(),
            tuple(fragments),
            len(fragments),
            narrow_fragment_type,
            narrow_fragment_number
        )
        
        cursor.execute("""
            WITH qualifying_bwb AS (
                SELECT
                    le.bwb_id
                FROM
                    public.law_element AS le
                    JOIN public.law_alias AS la ON le.bwb_id = la.bwb_id
                WHERE
                    lower(la.alias)  %s and
                    (le.type, le.number) in %s
                GROUP BY
                    le.bwb_id
                HAVING
                COUNT(*) = %s
            )
            SELECT
                le.*
            FROM
                public.law_element AS le
            JOIN
                qualifying_bwb qb ON le.bwb_id = qb.bwb_id
            WHERE
                le.type = %s AND le.number = %s;
        """, params)

        if cursor.rowcount > 1:
            logging.debug("link results in multiple resulting")
            return None

    
def find_laws_from_parts_with_n_cases(parts):
    with get_conn() as conn:
        cursor = conn.cursor()

        where_clause = []
        where_values = []
        if 'bwb_id' in parts:
            where_clause.append('l.bwb_id = ?')
            where_values.append(parts['bwb_id'])
        if 'type' in parts:
            where_clause.append('l.type = ?')
            where_values.append(parts['type'])
        if 'number' in parts:
            where_clause.append('lower(l.number) = lower(?)')
            where_values.append(parts['number'])

        where_clause = " AND ".join(where_clause)

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
            """, where_values)
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
            """, where_values)

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
                SELECT c.ecli_id, group_concat(distinct cl.source)
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
                SELECT c.ecli_id, STRING_AGG(distinct cl.source, ',')
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                JOIN legal_case c ON (cl.case_id = c.id)
                WHERE
                    l.bwb_id = %s AND
                    l.bwb_label_id = %s
                GROUP BY c.id
                LIMIT 5000
            """, (bwb_id, bwb_label_id,))

        return [[row[0], row[1].split(",")] for row in cursor.fetchall()]

def get_aliases_from_match(match, substring_search = True):
    resource_title, book_number = match["patterns"]["TITLE"], match["patterns"].get("BOOK", None)

    aliases = []
    if resource_title is None:
        return aliases
        if book_number is None:
            # article alone is (currently) not enough to retrieve books
            pass
        else:
            # search instances of '%boek {book_number}'
            # shouldnt happen, should always have book name!!!
            aliases = find_matching_aliases(f"boek {book_number}", wildcard=('l'))

    else:
        if book_number is None:
            # search instances of '{resource_title}%' (like BW% will return BW 1, BW 2, ...)
            aliases = find_matching_aliases(resource_title, wildcard=('r'))

        else:
            # search instances of '{resource_title} + {book_number}' (handle cases like Art. 5:123 BW -> Search "BW Boek 5")
            # TODO: I removed the wildcard=('r') because for BW book 1 it also returned 10. Do more testing.
            aliases = find_matching_aliases(f"{resource_title} boek {book_number}")
            if len(aliases) == 0:
                # search without 'boek {nr}' suffix
                aliases = find_matching_aliases(resource_title, wildcard=('r'))

        if len(aliases) == 0 and substring_search:
            # if above both didnt lead to results but we have a title, perform substring search
            # this (temporarily) fixes
            found = find_longest_alias_in_substring(resource_title)
            aliases = [found] if found is not None else aliases
    
    return aliases