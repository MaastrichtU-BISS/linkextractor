import re
from src.patterns import fix_matches, match_patterns_regex
from src.types import Fragment, Link
from src.utils import *

def extract_in_text(text, loose=False):
    """
    exrtact_in_text
    find and extract link references from a larger text

    strategy:
    1. extract all aliases found in the text
    2. 
    """

    # temp: this should be globalised
    DEBUG = logging.getLogger().getEffectiveLevel() == logging.DEBUG

    if DEBUG:
        disp_query = re.sub(r'\n+|\s+', ' ', text[0:128])+'...' if len(text) > 128 else text
        logging.debug(f"extract_in_text query: \"{disp_query}\"")
    
    start = time()
    aliases = find_aliases_in_text(text, True)
    logging.debug("time retrieve aliases: %s", time() - start)

    if DEBUG:
        if len(aliases) > 0:
            logging.debug("aliases:")
            for i, alias in enumerate(aliases):
                logging.debug(f"{i+1}) {alias}")
        else:
            logging.debug("no aliases were found in the query")

    start = time()
    matches = match_patterns_regex(text, aliases)
    logging.debug("time match patterns: %s", time() - start)

    results = []

    if len(matches) == 0 and loose:
        logging.debug("no matches found, expanding to loose search")
        if len(aliases) == 0:
            if DEBUG:
                logging.debug("no patterns found, so no results can be produced")
            return []
        else:
            if DEBUG:
                logging.debug("aliases found in query, so all aliases are considered as possible results")
            matches = []
            for alias in aliases:
                span = (None, None)
                span_search = text.find(alias)
                if span_search > -1:
                    span = (span_search, span_search+len(alias),)
                matches.append({
                    "span": span,
                    "patterns": {
                        "TITLE": alias
                    }
                })

    logging.debug("matches found: %s", len(matches))
    for i, match in enumerate(matches):
        logging.debug("%s) %s", i, match)   

        mapping = {
            'ARTICLE': 'artikel',
            'BOOK': 'boek',
            # 'SUBPARAGRAPH'
        }

        logging.debug(match['patterns']['TITLE'])
        fragments: Fragment = {mapping[k]:str(v) for k,v in match['patterns'].items() if k != 'TITLE' and v is not None} # pyright: ignore[reportAssignmentType]

        logging.debug("find laws with: alias: '%s', fragments: %s", match['patterns']['TITLE'], fragments)

        laws = find_laws(fragments, match['patterns']['TITLE'])

        for law in laws:
            results.append({
                'context': {
                    'span': match['span']
                },
                'resource': {
                    'name': law['title'],
                    'bwb_id': law['bwb_id'],
                    'bwb_label_id': law['bwb_label_id'],
                },
                'fragment': fragments
            })
        
        # aliases = get_aliases_from_match(match, False)

        # if DEBUG:
        #     logging.debug(f"{i+1}) Match at character positions {match['span'][0]} to {match['span'][1]} of pattern {match}:")
        # if len(aliases) == 0:
        #     if DEBUG:
        #         logging.debug(" -> NO RESULTS (shouldn't happend)")
        # else:
        #     for result in aliases:
        #         results.append(result)
        #         if DEBUG:
        #             logging.debug(f" -> {result['alias']} ({result['bwb_id']})")
    

    return results

def extract_exact(text: str, loose=False) -> List[Link]:
    """
    query_exact
    first, catch matches

    loose   requires finding patterns in the text to return results
    """

    # temp: this should be globalised
    DEBUG = logging.getLogger().getEffectiveLevel() == logging.DEBUG

    text = text.strip()

    if DEBUG:
        disp_query = re.sub(r'\n+|\s+', ' ', text[0:128])+'...' if len(text) > 128 else text
        logging.debug(f"extracty exact query: \"{disp_query}\"")

    start = time()
    matches = match_patterns_regex(text)
    logging.debug("time match patterns: %s", time() - start)

    # some manual fixes, such as matching 1:2 as book:art instead of article
    matches = fix_matches(matches)

    results: List[Link] = []

    # if no pattern matches, try find longest substring
    if len(matches) == 0 and loose:
        logging.debug("no matches found, expanding to loose search")

        aliases = find_matching_aliases(text, wildcard=('l', 'r'))

        if len(aliases) == 0:
            found = find_longest_alias_in_substring(text)
            aliases = [found] if found is not None else []

        for alias in aliases:
            # resources without fragments
            results.append({
                'resource': {
                    'name': alias['alias'],
                    'bwb_id': alias['bwb_id']
                }
            })
    else:
        logging.debug("matches found: %s", len(matches))
        for i, match in enumerate(matches):
            logging.debug("%s) %s", i, match)

            mapping = {
                'ARTICLE': 'artikel',
                'BOOK': 'boek',
                # 'SUBPARAGRAPH'
            }

            logging.debug(match['patterns']['TITLE'])
            fragments: Fragment = {mapping[k]:str(v) for k,v in match['patterns'].items() if k != 'TITLE' and v is not None} # pyright: ignore[reportAssignmentType]

            # logging.debug("find laws with: alias: '%s', bwb_id: %s, fragments: %s", match['patterns']['TITLE'], alias['bwb_id'], fragments)

            laws = find_laws(fragments, match['patterns']['TITLE'])

            for law in laws:
                results.append({
                    'resource': {
                        'name': law['title'],
                        'bwb_id': law['bwb_id'],
                        'bwb_label_id': law['bwb_label_id'],
                    },
                    'fragment': fragments
                })
            
            continue

            # old:
            aliases = get_aliases_from_match(match)

            if len(aliases) == 0:
                if DEBUG:
                    logging.debug("no aliases found")
            else:
                if DEBUG:
                    logging.debug(f"aliases found: {', '.join([alias['alias'] for alias in aliases])}")
                for alias in aliases:
                    parts = {
                        'bwb_id': alias['bwb_id']
                    }

                    mapping = {
                        'ARTICLE': 'article',
                        'BOOK': 'book',
                    }

                    for type, number in match['patterns'].items():
                        parts[mapping[type]] = number

                    elements = find_laws_from_parts(parts)
                    for element in elements:
                        results.append(element)

    if len(results) > 1:
        logging.warning("more results found for exact search")

    return results
