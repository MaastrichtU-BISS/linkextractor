import re
from src.patterns import fix_matches, match_patterns_regex
from src.types import Fragment, Link
from src.utils import *

def extract_in_text(text, loose=False, unique_spans=True):
    """
    exrtact_in_text
    find and extract link references from a larger text

    strategy:
    1. extract all aliases found in the text
    2. 
    """

    # TODO: this should be globalised
    DEBUG = logging.getLogger().getEffectiveLevel() == logging.DEBUG

    if DEBUG:
        disp_text = re.sub(r'\n+|\s+', ' ', text[0:128])+'...' if len(text) > 128 else text
        logging.debug(f"extract_in_text input text: \"{disp_text}\"")
    
    # retrieve aliases
    start = time()
    aliases = find_aliases_in_text(text, True)
    logging.debug("time retrieve aliases: %s", time() - start)
    if len(aliases) != 0:
        logging.debug("aliases found: %s", len(aliases))
        # for i, alias in enumerate(aliases):
        #     logging.debug(f"{i+1}) {alias}")
    else:
        logging.debug("no aliases were found in the query")

    # retrieve matches from text using aliases
    start = time()
    matches = match_patterns_regex(text, aliases)
    logging.debug("time match patterns: %s", time() - start)

    # fix some of the matches that need reformatting for specific casess
    matches = fix_matches(matches)

    # if loose search is enabled, consider individual aliases in the text as possible matches when if patterns were found.
    # TODO: reinforce specifically for the case of finding whole laws for wich a more elaborate pattern aside from the title 
    # is not available.
    results = []
    if len(matches) == 0 and loose:
        logging.debug("no matches found, expanding to loose search")
        if len(aliases) == 0:
            logging.debug("no patterns found, so no results can be produced")
            return []
        else:   
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

    # process each match to find an appropriately matching law
    span_record = []
    for i, match in enumerate(matches):
        logging.debug("%s) %s", i, match)

        mapping = {
            'ARTICLE': 'artikel',
            'BOOK': 'boek',
            'SUBPARAGRAPH': 'subparagraaf'
        }

        # construct fragments from a mapping of capture groups-names to types in the db and skip empty captures and the title capture
        fragments: Fragment = {mapping[k]:str(v) for k,v in match['patterns'].items() if k != 'TITLE' and v is not None} # pyright: ignore[reportAssignmentType]

        # find the related laws
        logging.debug("find laws with: alias: '%s', fragments: %s", match['patterns']['TITLE'], fragments)
        laws = find_laws(fragments, match['patterns']['TITLE'])

        # process each law
        for law in laws:
            if match['span'] in span_record and unique_spans == True:
                continue
            span_record.append(match['span'])

            results.append({
                'context': {
                    'span': match['span'],
                    'literal': match['literal']
                },
                'resource': {
                    'title': law['title'],
                    'bwb_id': law['bwb_id'],
                    'bwb_label_id': law['bwb_label_id'],
                },
                'fragment': fragments
            })

    return results

def extract_exact_old(text: str, loose=False) -> List[Link]:
    """
    query_exact
    first, catch matches

    loose   requires finding patterns in the text to return results
    """

    # temp: this should be globalised
    DEBUG = logging.getLogger().getEffectiveLevel() == logging.DEBUG

    text = text.strip()

    if DEBUG:
        disp_text = re.sub(r'\n+|\s+', ' ', text[0:128])+'...' if len(text) > 128 else text
        logging.debug(f"extract exact input text: \"{disp_text}\"")

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
                    'title': alias['alias'],
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
                        'title': law['title'],
                        'bwb_id': law['bwb_id'],
                        'bwb_label_id': law['bwb_label_id'],
                    },
                    'fragment': fragments
                })
    
    if len(results) > 1:
        logging.warning("more results found for exact search")

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
        disp_text = re.sub(r'\n+|\s+', ' ', text[0:128])+'...' if len(text) > 128 else text
        logging.debug(f"extract exact input text: \"{disp_text}\"")


    start = time()
    aliases = find_aliases_in_text(text, True)
    logging.debug("time retrieve aliases: %s", time() - start)

    if len(aliases) > 0:
        logging.debug("aliases found: %s", len(aliases))
    else:
        logging.debug("no aliases were found in the query")

    start = time()
    matches = match_patterns_regex(text, aliases)
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
                    'title': alias['alias'],
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
                        'title': law['title'],
                        'bwb_id': law['bwb_id'],
                        'bwb_label_id': law['bwb_label_id'],
                    },
                    'fragment': fragments
                })
    
    if len(results) > 1:
        logging.warning("more results found for exact search")

    return results
