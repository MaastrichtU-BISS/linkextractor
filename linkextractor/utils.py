import logging
from typing import Dict, Tuple, Union, List
import re
from linkextractor.db import get_conn
from linkextractor.types import Alias, AliasList, Fragment
from time import time
import os

_TRIE_CACHE = None
_TRIE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aliases.trie")

def get_trie():
    global _TRIE_CACHE
    import marisa_trie

    path = _TRIE_PATH
    
    if _TRIE_CACHE is not None:
        return _TRIE_CACHE
    else:
        if os.path.exists(path):
            # Load existing trie file
            start = time()
            trie = marisa_trie.Trie().load(path)
            _TRIE_CACHE = trie
            logging.debug("time loading trie file: %s", time() - start)
        else:
            # Else: build from DB
            start = time()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DISTINCT lower(alias) FROM law_alias")
                    aliases = []
                    for (alias,) in cur.fetchall():
                        norm = str(alias).lower()
                        aliases.append(norm)

            # Build trie
            trie = marisa_trie.Trie(aliases)
            trie.save(path)
            logging.debug("time building and saving trie file: %s", time() - start)
            _TRIE_CACHE = trie

    assert _TRIE_CACHE is not None, "_TRIE_CACHE could not be generaetd"
    return _TRIE_CACHE

def find_aliases_in_text(text, use_trie=False):
    # prefer Trie
    if use_trie:
        trie = get_trie()
        norm_text = text.lower()
        results = []
        for i in range(len(norm_text)):
            # Find longest alias that matches text[i:]
            matches = trie.prefixes(norm_text[i:])
            if matches:
                # take longest match
                alias = max(matches, key=len)
                # offset_start = i
                # offset_end = i + len(alias)
                results.append(alias)
        return results

    # performs WHERE ? LIKE column, instead of WHERE column LIKE ?
    with get_conn() as conn:
        with conn.cursor() as cur:

            # (wildcard) escaping of input not necessary since the input is the
            # column in the where clause, not the value
            # input_text_escaped = re.sub(r'([_%])', r'\\\1', input_text)

            cur.execute('''
                SELECT DISTINCT alias FROM law_alias
                WHERE lower(%s) LIKE '%%' || lower(alias) || '%%'
                LIMIT 50;
            ''', (text,))
            
            results = []
            for (alias,) in cur.fetchall():
                if re.search(rf"\b{re.escape(alias)}\b", text, flags=re.IGNORECASE):
                    results.append(alias)

            return results

def find_longest_alias_in_substring(input_text) -> Alias | None:
    # functions similar to find_aliases_in_text, but only does right wildcard and returns single result
    # (used for exact search)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT alias, bwb_id
                FROM law_alias
                WHERE %s ILIKE alias || '%%'
                ORDER BY LENGTH(alias) DESC
                LIMIT 1;
            ''', (input_text,))

            row = cur.fetchone()
            if not row:
                return None

            return {
                'alias': row[0],
                'bwb_id': row[1]
            }

def find_matching_aliases(name, wildcard=None) -> AliasList:
    with get_conn() as conn:
        with conn.cursor() as cur:
            name_escaped = re.sub(r'([_%])', r'\\\1', name)
            if wildcard is not None:
                if 'l' in wildcard:
                    name_escaped = '%'+name_escaped
                if 'r' in wildcard:
                    name_escaped = name_escaped+'%'

            cur.execute('''
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
            
            return [{
                'alias': row[0],
                'bwb_id': row[1]
            } for row in cur.fetchall()]

def find_laws(fragments: Fragment | None = None, alias: str | None = None, bwb_id: str | None = None):

    # assert alias is not None and len(alias.strip()) != 0, "alias should not be empty"
    assert (alias is not None and len(alias.strip()) != 0) ^ (bwb_id is not None), "alias should not be empty"
    assert fragments is not None and len(fragments) != 0, "list of fragments should not be empty"

    # order fragments based on specificity, ordered from broad (top) to narrow
    type_order = (
        'wet',
        'boek',
        'deel',
        'titeldeel',
        'hoofdstuk',
        'artikel',
        'paragraaf',
        # 'subparagraaf', # granularity of lid/subparagraph is not available in db so ommited
        'afdeling'
    )

    fragment_tuples: List[Tuple[str, str]] = [
        (type, str(number).lower()) for type, number in fragments.items()
        if type in type_order
    ]
    order_map = {law_type: index for index, law_type in enumerate(type_order)}
    fragment_tuples = sorted(fragment_tuples, key=lambda frag: order_map[frag[0]])
    
    # determine most narrow fragment
    narrow_fragment_type, narrow_fragment_number = fragment_tuples[-1]

    with get_conn() as conn:
        with conn.cursor() as cur:

            # if we have an alias
            if alias is not None and bwb_id is None:
                params = (
                    tuple(fragment_tuples),
                    alias.lower(),
                    len(fragment_tuples),
                    narrow_fragment_type,
                    narrow_fragment_number
                )
                
                logging.debug("params alias: %s", params)

                laws_query = f"""
                    WITH qualifying_bwb AS (
                        SELECT le.bwb_id
                        FROM (
                            SELECT bwb_id, bwb_label_id, type, number
                            FROM law_element
                            WHERE
                            (type, lower(number)) in %s
                        ) le
                        JOIN law_alias la ON le.bwb_id = la.bwb_id
                        WHERE lower(la.alias) = %s
                        GROUP BY le.bwb_id
                        HAVING COUNT(DISTINCT (type, lower(number))) = %s
                    )
                    SELECT
                        le.type, le.number, le.bwb_id, le.bwb_label_id, le.title
                    FROM
                        public.law_element AS le
                    JOIN
                        qualifying_bwb qb ON le.bwb_id = qb.bwb_id 
                    WHERE
                        le.type = %s AND lower(le.number) = %s
                    GROUP BY 
                        le.type, le.number, le.bwb_id, le.bwb_label_id, le.title;
                """

            # if a specific bwb_id is provided instead of an alias (in the case of substring-search alias)
            elif alias is None and bwb_id is not None:
                params = (
                    # bwb_id,
                    tuple(fragment_tuples),
                    bwb_id,
                    len(fragment_tuples),
                    narrow_fragment_type,
                    narrow_fragment_number
                )
                
                logging.debug("params bwb: %s", params)

                laws_query = f"""
                    WITH qualifying_bwb AS (
                        SELECT le.bwb_id
                        FROM (
                            SELECT bwb_id, bwb_label_id, type, number
                            FROM law_element
                            WHERE
                                (type, lower(number)) in %s
                        ) le
                        JOIN law_alias la ON le.bwb_id = la.bwb_id
                        WHERE la.bwb_id = %s
                        GROUP BY le.bwb_id
                        HAVING COUNT(DISTINCT (type, lower(number))) = %s
                    )
                    SELECT
                        le.type, le.number, le.bwb_id, le.bwb_label_id, le.title
                    FROM
                        public.law_element AS le
                    JOIN
                        qualifying_bwb qb ON le.bwb_id = qb.bwb_id 
                    WHERE
                        le.type = %s AND lower(le.number) = %s
                    GROUP BY 
                        le.type, le.number, le.bwb_id, le.bwb_label_id, le.title;
                """

            start = time()
            cur.execute(laws_query, params)
            logging.debug("time query find_laws: %s", time() - start)
            logging.debug("results query find_laws: %s", cur.rowcount)
            # logging.debug("query find_laws: %s", laws_query)

            return [
                {
                    'type': law_row[0],
                    'number': law_row[1],
                    'bwb_id': law_row[2],
                    'bwb_label_id': law_row[3],
                    'title': law_row[4],
                } for law_row in cur.fetchall()
            ]

def get_cases_by_bwb_and_label_id(bwb_id, bwb_label_id):
    """
    Returns ECLI-id's related to the bwb and label_id
    """

    assert bwb_id is not None
    assert bwb_label_id is not None

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
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

            return [[row[0], row[1].split(",")] for row in cur.fetchall()]


def get_amount_cases_by_bwb_and_label_ids(ids_list: List[Tuple]):
    """
    Returns a lookup list with the amount of cases related to a list of tuples of bwb- and bwb_label-ids
    """

    result = []

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT l.bwb_id, l.bwb_label_id, COUNT(DISTINCT cl.case_id)
                FROM law_element l
                JOIN case_law cl ON (cl.law_id = l.id)
                WHERE
                    (l.bwb_id, l.bwb_label_id) IN
                    %s
                GROUP BY l.bwb_id, l.bwb_label_id
            """, (tuple(ids_list),))
            
            results = cur.fetchall()

            id_lookup = {(row[0], row[1]): row[2] for row in results}

            return id_lookup