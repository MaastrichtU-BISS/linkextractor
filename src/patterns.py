from typing import Dict, Literal
import re

RefType = Literal["BOEK", "ARTIKEL"]
RefDict = Dict[RefType, re.Pattern]

# pattern class
class PT:
    # zero, one or more whistespaces
    WS_0 = "\s*"

    # one or more whitespaces
    WS = "\s+"
    
    # a comma with zero or more spaces, or one or more spaces
    COMMA_SPACE = rf"(?:[,]{WS_0}|{WS})" # <-

    # various ways some literals can be written in (artikel: art, art., artt., artt, ...)
    LITERAL: RefDict = {
        "BOEK": r"(?:boek|bk\.?)",
        "ARTIKEL": r"(?:artikel(?:en)?|artt?\.?)"
    }

    # identifiers for the mentioned ref types
    ID: RefDict = {
        "BOEK": r"([0-9]+)",
        "ARTIKEL": r"(\d+(?:\.\d+)?[a-zA-Z]?(?:-[a-zA-Z0-9]+)?)"  # matches: 1, 1.12, 1.2a, 1b, 1b-c, 1-2
    }
    
    LIDWOORDEN = r"(?:de|het)" # -> 2
    OPT_TUSSENVOEGSEL = rf"(?:{WS}van(?:{WS}{LIDWOORDEN})?)?" # -> 1*2*2 = 4

    ALIASES = staticmethod(
        lambda matches:
            "(" + "|".join(re.escape(match) for match in matches) + ")" 
                if matches is not None else 
            r"(.+?)"
    )

    # def aliases(names):
    #     return "(" + "|".join(re.escape(match) for match in names) + ")" if names is not None else r"(.+?)"
    
    @staticmethod
    def patterns(aliases):
        ALIASES = PT.ALIASES(aliases)

        return [
            # "Artikel 5 van het boek 7 van het BW"
            # "Artikel 5 boek 7 BW"
            (
                PT.LITERAL['ARTIKEL'] +
                PT.WS +
                PT.ID['ARTIKEL'] +
                PT.OPT_TUSSENVOEGSEL +
                PT.WS +
                PT.LITERAL['BOEK'] +
                PT.WS +
                PT.ID['BOEK'] +
                PT.OPT_TUSSENVOEGSEL +
                PT.WS +
                ALIASES
            , ("article", "book_number", "book_name",)),

            # "Artikel 61 Wet toezicht trustkantoren 2018"
            (
                PT.LITERAL['ARTIKEL'] +
                PT.WS +
                PT.ID['ARTIKEL'] +
                PT.OPT_TUSSENVOEGSEL +
                PT.WS +
                rf"(?:{PT.LITERAL['BOEK']}{PT.WS})?" +
                ALIASES
            , ("article", "book_name",)),

            # "Artikel 7:658 van het BW"
            (
                PT.LITERAL['ARTIKEL'] +
                PT.WS +
                PT.ID['BOEK'] +
                ":" +
                PT.ID['ARTIKEL'] +
                PT.OPT_TUSSENVOEGSEL +
                PT.WS + 
                rf"(?:{PT.LITERAL['BOEK']}{PT.WS})?" +
                ALIASES
            , ("book_number", "article", "book_name",)),
            
            # "Burgerlijk Wetboek Boek 7, Artikel 658"
            (
                ALIASES +
                rf"(?:{PT.WS}{PT.LITERAL['BOEK']}{PT.WS}{PT.ID['BOEK']})?" +
                PT.COMMA_SPACE +
                PT.LITERAL['ARTIKEL'] +
                PT.WS +
                PT.ID['ARTIKEL']
            , ("book_name", "book_number", "article",)),
            
            # "3:2 awb" -> also not parsed on linkeddata
            # TODO: make this only match if not other match found???
            # (rf"{PT.ID['BOEK']}:{PT.ID['ARTIKEL']}{PT.WS}{PT.OPT_TUSSENVOEGSEL}{PT.pts_types['boek']}?{PT.WS_0}{ALIASES}", ("book_number", "article", "book_name")),
        ]

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
