import re
from linkextractor.patterns import fix_matches, get_atoms, match_patterns_regex, sub_pattern_placeholders
from linkextractor.types import Fragment, Link
from linkextractor.utils import *
from copy import deepcopy

def extract_links(text, exact=False, loose=False, use_trie=True):
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
        logging.debug(f"extract links input text: \"{disp_text}\"")
    
    aliases = None
    if not exact:
        # retrieve aliases
        start = time()
        aliases = find_aliases_in_text(text, use_trie)
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
    if len(matches) == 0 and loose and aliases:
        logging.debug("no matches found, expanding to loose search")
        if aliases is None:
            logging.debug("exact search, hence retrieving aliases now (after matching)")
            start = time()
            aliases = find_aliases_in_text(text, use_trie)
            logging.debug("time retrieve aliases: %s", time() - start)
            
        if len(aliases) == 0:
            logging.debug("no patterns found, so no results can be produced")
            return []
        else:
            logging.debug(f"{len(aliases)} aliases found in query, which all will be used as matches")
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


    mapping = {
        'ARTICLE': 'artikel',
        'BOOK': 'boek',
        'SUBPARAGRAPH': 'subparagraaf'
    }

    pattern_conjunction = get_atoms()['LITERAL|CONJUNCTION']

    # process each match to find an appropriately matching law
    span_record = []
    for i, match in enumerate(matches):
        logging.debug("%s) %s", i, match)


        sub_matches = []
        if not exact and 'ARTICLES' in match['patterns']:
            logging.debug("multiple parts in match at span %s", match['span'])
            # if a match contains multiple references (to articles), then split those up, remove
            # the ARTICLES match and place each individual article in the ARTICLE-pattern 
            parts = re.split(pattern_conjunction, match['patterns']['ARTICLES'])
            for part in parts:
                part = part.strip()
                if len(part) == 0: continue
                logging.debug("part: \"%s\"", part)
                new_match = deepcopy(match)
                del new_match['patterns']['ARTICLES']
                new_match['patterns']['ARTICLE'] = part
                sub_matches.append(new_match)
        else:
            sub_matches = [match]

        for sub_match in sub_matches:

            # print("AAA", sub_match['patterns'].items())

            # construct fragments from a mapping of capture groups-names to types in the db and skip empty captures and the title capture
            fragments: Fragment = {
                mapping[k]:str(v)
                for k,v in sub_match['patterns'].items()
                if k != 'TITLE'
                # if k != 'SUBPARAGRAPH' # no entries exist in the database for this type
                if v is not None
            } # pyright: ignore[reportAssignmentType]

            # find the related laws
            logging.debug("find laws with: alias: '%s', fragments: %s", sub_match['patterns']['TITLE'], fragments)
            laws = find_laws(fragments, alias=sub_match['patterns']['TITLE'])

            if len(laws) == 0:
                longest_alias = find_longest_alias_in_substring(sub_match['patterns']['TITLE'])
                if longest_alias is not None:
                    laws = find_laws(fragments, bwb_id=longest_alias['bwb_id'])

            # process each law
            for law in laws:
                # ensure unique spans for each span-fragment combination
                span_lookup = (sub_match['span'], tuple(fragments.items()))
                if span_lookup in span_record:
                    continue
                span_record.append(span_lookup)

                results.append({
                    'context': {
                        'span': sub_match['span'],
                        'literal': sub_match['literal']
                    },
                    'resource': {
                        'title': law['title'],
                        'bwb_id': law['bwb_id'],
                        'bwb_label_id': law['bwb_label_id'],
                    },
                    'fragment': fragments
                })
    
    
    if exact and len(results) > 1:
        logging.warning("more than one result found for exact search")

    return results
