from src.utils import *

def query_in_text(query, db_name):
    print(f"Query: \"{query}\"")

    aliases = find_aliases_in_text(query, db_name)

    print("Aliases:")
    for i, alias in enumerate(aliases):
        print(f"{i+1}) {alias}")
    
    matches = match_patterns_regex(query, aliases, db_name=db_name)
    
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
                        "book_name": alias,
                        "book_number": None,
                        "article": None
                    }
                })

    print("Matches:")
    for i, match in enumerate(matches):
        match["patterns"]["book_name"]
        
        book_name, book_number = match["patterns"]["book_name"], match["patterns"].get("book_number", None)

        results = []
        if book_name is None and book_number is None:
            # article alone is not enough to retrieve books
            pass
        elif book_name is None and book_number is not None:
            # search instances of '%boek {book_number}'
            # shouldnt happen, should always have book name!!!
            results = find_matching_aliases(f"boek {book_number}", wildcard=('l'), db_name=db_name)

        elif book_name is not None and book_number is None:
            # search instances of '{book_name}%' (like BW% will return BW 1, BW 2, ...)
            results = find_matching_aliases(book_name, wildcard=('r'), db_name=db_name)

        elif book_name is not None and book_number is not None:
            # search instances of '{book_name} + {book_number}' (handle cases like Art. 5:123 BW -> Search "BW Boek 5")
            results = find_matching_aliases(f"{book_name} boek {book_number}", wildcard=('r'))
            if len(results) == 0:
                results = find_matching_aliases(book_name, wildcard=('r'), db_name=db_name)

        print(f"{i+1}) Match at character positions {match['span'][0]} to {match['span'][1]} of pattern {match}:")
        if len(results) == 0:
            print(" -> NO RESULTS (shouldn't happend)")
        else:
            for result in results:
                end_results.append(result)
                print(f" -> {result[0]} ({result[1]})")
    print()
    return end_results
    
def query_exact(query: str, db_name="database.db"):
    query = query.strip()
    results = []

    matches = match_patterns_regex(query)
    if len(matches) == 0:
        aliases = find_matching_aliases(query, wildcard=('l', 'r'), db_name=db_name)
        if len(aliases) == 0:
            found = find_longest_alias_in_substring(query, db_name=db_name)
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
            if not 'book_name' in match['patterns']:
                continue
        
            book_name, book_number = match["patterns"]["book_name"], match["patterns"].get("book_number", None)

            aliases = []
            if book_name is None:
                if book_number is None:
                    # article alone is (currently) not enough to retrieve books
                    pass
                elif book_name is None and book_number is not None:
                    # search instances of '%boek {book_number}'
                    # shouldnt happen, should always have book name!!!
                    aliases = find_matching_aliases(f"boek {book_number}", wildcard=('l'), db_name=db_name)

            elif book_name is not None:
                if book_number is None:
                    # search instances of '{book_name}%' (like BW% will return BW 1, BW 2, ...)
                    aliases = find_matching_aliases(book_name, wildcard=('r'), db_name=db_name)

                elif book_number is not None:
                    # search instances of '{book_name} + {book_number}' (handle cases like Art. 5:123 BW -> Search "BW Boek 5")
                    aliases = find_matching_aliases(f"{book_name} boek {book_number}", wildcard=('r'), db_name=db_name)
                    if len(aliases) == 0:
                        # search without 'boek {nr}' suffix
                        aliases = find_matching_aliases(book_name, wildcard=('r'), db_name=db_name)
                
                if len(aliases) == 0:
                    # if above both didnt lead to results, perform substring match
                    # this (temporarily) fixes 
                    found = find_longest_alias_in_substring(book_name, db_name=db_name)
                    aliases = [found] if found is not None else aliases

            if len(aliases) == 0:
                # print(" -> NO RESULTS (shouldn't happend)")
                pass
            else:
                for alias in aliases:
                    result = {
                        'resource': {
                            'name': alias[0],
                            'id': alias[1]
                        }
                    }
                    if 'article' in match['patterns']:
                        result['article'] = match['patterns']['article']
                    if 'book_number' in match['patterns']:
                        result['book'] = match['patterns']['book_number']
                    results.append(result)

    return results
