from typing import Dict, Literal
import re

RefType = Literal["BOEK", "ARTIKEL"]
RefDict = Dict[RefType, re.Pattern]

# pattern class
class PT:
    # zero, one or more whistespaces
    WS_0 = r"\s*"

    # one or more whitespaces
    WS = r"\s+"
    
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
