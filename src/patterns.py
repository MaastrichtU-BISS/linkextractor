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

# NEW PATTERN

def capture(name: str, pattern: re.Pattern):
    return rf"(?P<{name}>{pattern})"

# Define your patterns using curly braces as placeholders.
PT_ATOMS = {
    "WS_0": r"\s*",
    "WS": r"\s+",
    "COMMA_SPACE": r"(?:[,]{WS_0}|{WS})",

    "LITERAL|BOOK": r"(?:boek|bk\.?)",
    "LITERAL|SUBPARAGRAPH": r"lid",
    "LITERAL|ARTICLE": r"(?:artikel(?:en)?|artt?\.?)",

    "ID|BOOK": capture('BOOK', r"[0-9]+"),
    "ID|SUBPARAGRAPH": capture("SUBPARAGRAPH", r"\d+"),
    # "ID|ARTICLE": capture('ARTICLE', r"\d+(?:\.\d+)?[a-zA-Z]?(?:-[a-zA-Z0-9]+)?(?:{WS}{LITERAL|SUBPARAGRAPH}{WS}{ID|SUBPARAGRAPH})"),
    "ID|ARTICLE": capture('ARTICLE', r"\d+(?:\.\d+)?[a-zA-Z]?(?:-[a-zA-Z0-9]+)?") + r"(?:{WS}{LITERAL|SUBPARAGRAPH}{WS}{ID|SUBPARAGRAPH})?",

    "LIDWOORDEN": r"(?:de|het)",
    "TUSSENVOEGSEL": r"(?:{WS}van(?:{WS}{LIDWOORDEN})?)",

    "TITLE": capture('TITLE', r".+?")
}


PT_REFS = [
    # "Artikel 5 van het boek 7 van het BW"
    # "Artikel 5 boek 7 BW"
    r'''
        {LITERAL|ARTICLE}
        {WS}
        {ID|ARTICLE}
        {TUSSENVOEGSEL}?
        {WS}
        {LITERAL|BOOK}
        {WS}
        {ID|BOOK}
        {TUSSENVOEGSEL}?
        {WS}
        {TITLE}
    ''',

    # "Artikel 61 Wet toezicht trustkantoren 2018"
    r'''
        {LITERAL|ARTICLE}
        {WS}
        {ID|ARTICLE}
        {TUSSENVOEGSEL}?
        {WS}
        (?:{LITERAL|BOOK}{WS})?
        {TITLE}
    ''',

    # "Artikel 7:658 van het BW"
    r'''
        {LITERAL|ARTICLE}
        {WS}
        {ID|BOOK}:{ID|ARTICLE}
        {TUSSENVOEGSEL}?
        {WS}
        (?:{LITERAL|BOOK}{WS})?
        {TITLE}
    ''',

    # "Burgerlijk Wetboek Boek 7, Artikel 658"
    r'''
        {TITLE}
        (?:{WS}{LITERAL|BOOK}{WS}{ID|BOOK})?
        {COMMA_SPACE}
        {LITERAL|ARTICLE}
        {WS}
        {ID|ARTICLE}
    ''',

    # "3:2 awb" -> also not parsed on linkeddata
]

def map_pattern_using_format(pattern, mapping):
    """
    Recursively substitute the placeholders in `pattern` with their corresponding values
    in `mapping` until the pattern is fully resolved.
    """
    previous = None
    current = pattern
    while previous != current:
        previous = current
        # Use the format method to replace placeholders.
        current = current.format(**mapping)
    
    return current

placeholder_pattern = re.compile(r'\{([^{}]+)\}')
def sub_pattern_placeholders(pattern, mapping):
    """
    Iteratively replace placeholders in s with their corresponding values
    in mapping until no further substitutions are made.
    """
    current = pattern
    
    max_iterations = 10
    i = 0
    while i < max_iterations:
        i+=1
        new_s = placeholder_pattern.sub(lambda m: mapping.get(m.group(1), m.group(0)), current)
        if new_s == current:
            break
        current = new_s
    
    return current

def get_patterns(patterns, mapping, anchors=False):
    compiled_patterns = []
    
    for pattern in patterns:
        mapped = sub_pattern_placeholders(pattern, mapping)
        if anchors:
            mapped = rf"^\s*{mapped}\s*$"
        # print("-> ", re.sub(r"[\s\n]+", "", mapped))
        compiled_patterns.append(re.compile(mapped, re.VERBOSE | re.IGNORECASE))

    return compiled_patterns

if __name__=="__main__":
    print("test")

    test_pat = r"^\s*(?:artikel(?:en)?|artt?\.?)\s+(?P<BOOK>[0-9]+):(?P<ARTICLE>\d+(?:\.\d+)?[a-zA-Z]?(?:-[a-zA-Z0-9]+)?)(?:\s+lid\s+(?P<SUBPARAGRAPH>\d+))?(?:\s+van(?:\s+(?:de|het))?)?\s+(?:(?:boek|bk\.?)\s+)?(?P<TITLE>.+?)\s*$"
    test_str = "Art. 5:1 lid 2 BW"
    first = re.finditer(test_pat, test_str, re.IGNORECASE)
    print(next(first).groupdict())
    exit()

    titles = ["BW", "Ar"]
    pt_titles = capture("TITLE", "|".join(re.escape(title) for title in titles))
    
    patterns = get_patterns(PT_REFS, {**PT_ATOMS, "TITLE": pt_titles})

    # Test the regex.
    test_string = "Artikel 5 van boek 7 van het BW"
    for pattern in patterns:
        for match in re.finditer(pattern, test_string):
            print("span", match.span())
            print("group", match.groupdict())