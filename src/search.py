import re
from src.patterns import fix_matches, match_patterns_regex
from src.types import Link
from src.utils import *

def query_in_text(query):
    """
    query_in_text
    find and extract link references from a larger text

    strategy:
    1. extract all aliases found in the text
    2. 
    """

    # temp: this should be globalised
    DEBUG = logging.getLogger().getEffectiveLevel() == logging.DEBUG

    logging.debug("Query: \"%s\"", re.sub(r'\n+|\s+', ' ', query[0:128])+'...' if len(query) > 128 else query)

    aliases = find_aliases_in_text(query)

    if DEBUG:
        if len(aliases) > 0:
            logging.debug("Aliases:")
            for i, alias in enumerate(aliases):
                logging.debug(f"{i+1}) {alias}")
        else:
            logging.debug("No aliases were found in the query")

    matches = match_patterns_regex(query, aliases)

    results = []

    if len(matches) == 0:
        if len(aliases) == 0:
            if DEBUG:
                logging.debug("No patterns or aliases were found in the query, so no results can be produced")
            return []
        else:
            if DEBUG:
                logging.debug("No patterns but aliases found in query, so all aliases are considered as possible results")
            matches = []
            for alias in aliases:
                span = (None, None)
                span_search = query.find(alias)
                if span_search > -1:
                    span = (span_search, span_search+len(alias),)
                matches.append({
                    "span": span,
                    "patterns": {
                        "TITLE": alias,
                        "BOOK": None,
                        "ARTICLE": None
                    }
                })

    if DEBUG:
        logging.debug("Matches:")
    for i, match in enumerate(matches):
        if not 'TITLE' in match['patterns']:
            continue

        aliases = get_aliases_from_match(match, False)

        if DEBUG:
            logging.debug(f"{i+1}) Match at character positions {match['span'][0]} to {match['span'][1]} of pattern {match}:")
        if len(aliases) == 0:
            if DEBUG:
                logging.debug(" -> NO RESULTS (shouldn't happend)")
        else:
            for result in aliases:
                results.append(result)
                if DEBUG:
                    logging.debug(f" -> {result['alias']} ({result['bwb_id']})")
    if DEBUG:
        logging.debug("")
    return results

def extract_links_exact(text: str, loose=False) -> List[Link]:
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
        logging.debug(f"Query: \"{disp_query}\"")

    matches = match_patterns_regex(text)

    # some manual fixes, such as matching 1:2 as book:art instead of article
    matches = fix_matches(matches)

    results: List[Link] = []

    # if no pattern matches, try find longest substring
    if len(matches) == 0:
        logging.debug("No matches found")
        if not loose:
            if DEBUG:
                logging.debug("No patterns were found in the text and loose search is disabled")
            return []

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
        logging.debug("Matches found: %s", len(matches))
        for i, match in enumerate(matches):
            logging.debug("%s) %s", i, match)
            if not 'TITLE' in match['patterns']:
                continue

            aliases = get_aliases_from_match(match)

            if len(aliases) == 0:
                if DEBUG:
                    logging.debug("No aliases found")
            else:
                if DEBUG:
                    logging.debug(f"Aliases found: {', '.join([alias['alias'] for alias in aliases])}")
                for alias in aliases:
                    parts = {
                        'bwb_id': alias['bwb_id']
                    }

                    if 'ARTICLE' in match['patterns']:
                        parts['article'] = match['patterns']['ARTICLE']
                    elif 'BOOK' in match['patterns']:
                        parts['book'] = match['patterns']['ARTICLE']
                    else:
                        continue # temporarily

                    elements = find_laws_from_parts(parts)
                    for element in elements:
                        results.append(element)

    return results
