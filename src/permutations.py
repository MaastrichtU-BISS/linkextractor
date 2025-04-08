import re
import exrex
from utils import get_aliases_of_ids
from search import query_exact
from patterns import PTP

def query_perms(query: str, debug: bool = True, db_name: str = "database.db"):

    exact_matches = query_exact(query, db_name)

    exact_aliases = []
    identifiers = {
        'BOEK': [],
        'ARTIKEL': [],
    }

    for exact_match in exact_matches:
        # map from english lowercase in exact_match to uppercase dutch in identifiers
        if exact_match['article'] and exact_match['article'] not in identifiers['ARTIKEL']:
            identifiers['ARTIKEL'].append(exact_match['article'])
        if exact_match['book'] and exact_match['book'] not in identifiers['BOEK']:
            identifiers['BOEK'].append(exact_match['book'])
        
        aliases = get_aliases_of_ids(exact_match['resource']['id'], db_name=db_name)
        for alias in aliases:
            exact_aliases.append(alias)

    # large_regex = construct_permutations_given_text(exact_aliases, identifiers)
    large_regex = PTP.pattern(exact_aliases, identifiers)
    # print(large_regex)

    debug and print("Permutations pattern:", large_regex)
    debug and print("Permutations estimated amount:", exrex.count(large_regex, 2))
    debug and print("Permutations:")

    perms = []

    i = 1
    for writing in exrex.generate(large_regex, 2):
        # print(writing)
        debug and print(i, writing)
        perms.append(writing)
        i+=1

        if i>10000:
            break
    
    return perms

    # print(regex)