import re
import exrex
from src.utils import get_aliases_of_ids
from src.search import query_exact
from src.patterns import PT

class PTP(PT):
    WS_0 = r"[ ]?"
    WS = r"[ ]"

    # we have to repeat these, since it needs to use the new WS. should come up with better solution
    COMMA_SPACE = rf"(?:[,]{WS_0}|{WS})"
    OPT_TUSSENVOEGSEL = rf"(?:{WS}van(?:{WS}{PT.LIDWOORDEN})?)?" # -> 1*2*2 = 4
    
    @staticmethod
    def pattern(aliases, identifiers):
        ALIASES = PTP.ALIASES(aliases)

        ID = PTP.ID
        if identifiers['BOEK']:
            ID['BOEK'] = "(" + "|".join(re.escape(n) for n in identifiers['BOEK']) + ")" # <- typically 1
        if identifiers['ARTIKEL']:
            ID['ARTIKEL'] = "(" + "|".join(re.escape(n) for n in identifiers['ARTIKEL']) + ")" # <- typically 1
            
        patterns = [
            # "Artikel 5 van het boek 7 van het BW"
            # "Artikel 5 boek 7 BW"
            (
                PTP.LITERAL['ARTIKEL'] +
                PTP.WS +
                ID['ARTIKEL'] +
                PTP.OPT_TUSSENVOEGSEL +
                PTP.WS +
                PTP.LITERAL['BOEK'] +
                PTP.WS +
                ID['BOEK'] +
                PTP.OPT_TUSSENVOEGSEL +
                PTP.WS +
                ALIASES
            , ("article", "book_number", "book_name")),
            # -> 6 * 1 * 1 * 1 * 4 * 3 * 1 * 1 * 1 * 4 * 1 * n = 576*n 

            # "Artikel 61 Wet toezicht trustkantoren 2018"
            (
                PTP.LITERAL['ARTIKEL'] +
                PTP.WS +
                ID['ARTIKEL'] +
                PTP.OPT_TUSSENVOEGSEL +
                PTP.WS +
                rf"(?:{PTP.LITERAL['BOEK']}{PTP.WS})?" +
                ALIASES
            , ("article", "book_name")),
            # -> 6 * 1 * 1 * 1 * 4 * 3*2 * 2 * n = 288*n

            # "Artikel 7:658 van het BW"
            (
                PTP.LITERAL['ARTIKEL'] +
                PTP.WS +
                ID['BOEK'] +
                ":" +
                ID['ARTIKEL'] +
                PTP.OPT_TUSSENVOEGSEL +
                PTP.WS +
                rf"(?:{PTP.LITERAL['BOEK']}{PTP.WS})?" +
                ALIASES
            , ("book_number", "article", "book_name")),
            # -> 3 * 1 * 1 * 1 * 4 * 3*2 * 2 * n = 72*n
            
            # "3:2 awb" -> also not parsed on linkeddata
            # (rf"{pt_elementnummer}:{pt_elementnummer}{WS}{PT.OPT_TUSSENVOEGSEL}{pts_types['boek']}?{WS_0}{pt_matches}", ("book_number", "article", "book_name")),
            
            # "Burgerlijk Wetboek Boek 7, Artikel 658"
            (
                ALIASES +
                "(?:{PTP.WS}{PTP.LITERAL['BOEK']}{PTP.WS}{ID['BOEK']})?" +
                PTP.COMMA_SPACE +
                PTP.LITERAL['ARTIKEL'] +
                PTP.WS +
                ID['ARTIKEL']
            , ("book_name", "book_number", "article")),
            # -> n * (1*3*1*1)*2 *2 *2*6*1*1 = 144*n
        ]

        total_regex = re.compile(r"(?:" + ")|(".join([p[0] for p in patterns]) + ")", re.VERBOSE | re.IGNORECASE)
        total_pattern = total_regex.pattern

        return total_pattern

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