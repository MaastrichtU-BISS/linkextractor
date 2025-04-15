from typing import Dict, Literal
import re

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

# patterns for either recognizing references in larger text or as exact
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

    # "Burgerlijk Wetboek Boek 7, Artikel 658"
    r'''
        {TITLE}
        (?:{WS}{LITERAL|BOOK}{WS}{ID|BOOK})?
        {COMMA_SPACE}
        {LITERAL|ARTICLE}
        {WS}
        {ID|ARTICLE}
    ''',

    # "Artikel 7:658 van het BW" -> requires hardcoded interpretation after
    # "Artikel 4:8 van de Algemene wet bestuursrecht (hoor en wederhoor)"
    r'''
        {LITERAL|ARTICLE}
        {WS}
        {ID|ARTICLE}
        {TUSSENVOEGSEL}?
        {WS}
        {TITLE}
    ''',
]

# patterns only for exact matching
PT_REFS_EXACT = [
    # "3:2 awb"
    r'''
        {ID|BOOK}:{ID|ARTICLE}
        {TUSSENVOEGSEL}?
        {WS}
        (?:{LITERAL|BOOK}{WS})?
        {TITLE}
    ''',
]

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

def get_patterns(mapping, exact=False):
    compiled_patterns = []
    
    if exact:
        patterns = PT_REFS + PT_REFS_EXACT
    else:
        patterns = PT_REFS

    for pattern in patterns:
        mapped = sub_pattern_placeholders(pattern, mapping)
        if exact:
            mapped = rf"^\s*{mapped}\s*$"
        compiled_patterns.append(re.compile(mapped, re.VERBOSE | re.IGNORECASE))

    return compiled_patterns
