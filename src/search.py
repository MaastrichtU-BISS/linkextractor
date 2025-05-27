from src.patterns import fix_matches, match_patterns_regex
from src.utils import *

def query_in_text(query):
    """
    Find matches in a larger text. This function is in progress and not finished yet.
    """
    print(f"Query: \"{query}\"")

    aliases = find_aliases_in_text(query)

    print("Aliases:")
    for i, alias in enumerate(aliases):
        print(f"{i+1}) {alias}")
    
    matches = match_patterns_regex(query, aliases)
    
    end_results = []

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
                        "TITLE": alias,
                        "BOOK": None,
                        "ARTICLE": None
                    }
                })

    print("Matches:")
    for i, match in enumerate(matches):
        # match["patterns"]["resource_title"]
        
        resource_title, book_number = match["patterns"]["TITLE"], match["patterns"].get("BOOK", None)

        results = []
        if resource_title is None and book_number is None:
            # article alone is not enough to retrieve books
            pass
        elif resource_title is None and book_number is not None:
            # search instances of '%boek {book_number}'
            # shouldnt happen, should always have book name!!!
            results = find_matching_aliases(f"boek {book_number}", wildcard=('l'))

        elif resource_title is not None and book_number is None:
            # search instances of '{resource_title}%' (like BW% will return BW 1, BW 2, ...)
            results = find_matching_aliases(resource_title, wildcard=('r'))

        elif resource_title is not None and book_number is not None:
            # search instances of '{resource_title} + {book_number}' (handle cases like Art. 5:123 BW -> Search "BW Boek 5")
            results = find_matching_aliases(f"{resource_title} boek {book_number}", wildcard=('r'))
            if len(results) == 0:
                results = find_matching_aliases(resource_title, wildcard=('r'))

        print(f"{i+1}) Match at character positions {match['span'][0]} to {match['span'][1]} of pattern {match}:")
        if len(results) == 0:
            print(" -> NO RESULTS (shouldn't happend)")
        else:
            for result in results:
                end_results.append(result)
                print(f" -> {result[0]} ({result[1]})")
    print()
    return end_results

def query_exact(query: str):
    query = query.strip()
    results = []

    matches = match_patterns_regex(query)

    # some manual fixes, such as matching 1:2 as book:art instead of article
    matches = fix_matches(matches)

    # if no pattern matches, try find longest substring
    if len(matches) == 0:
        aliases = find_matching_aliases(query, wildcard=('l', 'r'))
        if len(aliases) == 0:
            found = find_longest_alias_in_substring(query)
            aliases = [found] if found is not None else []
        
        for alias in aliases:
            result = {
                'resource': {
                    'name': alias[0],
                    'id': alias[1]
                }
            }
    else:
        for i, match in enumerate(matches):
            if not 'TITLE' in match['patterns']:
                continue
        
            resource_title, book_number = match["patterns"]["TITLE"], match["patterns"].get("BOOK", None)

            aliases = []
            if resource_title is None:
                if book_number is None:
                    # article alone is (currently) not enough to retrieve books
                    pass
                elif resource_title is None and book_number is not None:
                    # search instances of '%boek {book_number}'
                    # shouldnt happen, should always have book name!!!
                    aliases = find_matching_aliases(f"boek {book_number}", wildcard=('l'))

            elif resource_title is not None:
                if book_number is None:
                    # search instances of '{resource_title}%' (like BW% will return BW 1, BW 2, ...)
                    aliases = find_matching_aliases(resource_title, wildcard=('r'))

                elif book_number is not None:
                    # search instances of '{resource_title} + {book_number}' (handle cases like Art. 5:123 BW -> Search "BW Boek 5")
                    # TODO: I removed the wildcard=('r') because for BW book 1 it also returned 10. Do more testing.
                    aliases = find_matching_aliases(f"{resource_title} boek {book_number}")
                    if len(aliases) == 0:
                        # search without 'boek {nr}' suffix
                        aliases = find_matching_aliases(resource_title, wildcard=('r'))
                
                if len(aliases) == 0:
                    # if above both didnt lead to results, perform substring match
                    # this (temporarily) fixes 
                    found = find_longest_alias_in_substring(resource_title)
                    aliases = [found] if found is not None else aliases

            if len(aliases) == 0:
                # print(" -> NO RESULTS (shouldn't happend)")
                pass
            else:
                for alias in aliases:
                    parts = {
                        'bwb_id': alias[1]
                    }

                    if 'ARTICLE' in match['patterns']:
                        parts['type'] = 'artikel'
                        parts['number'] = match['patterns']['ARTICLE']
                    else:
                        continue # temporarily
                    
                    elements = find_laws_from_parts(parts)
                    for element in elements:
                        results.append(element)

    return results
