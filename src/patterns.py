from typing import Dict, List, Literal, Union
import re
import logging

def capture(name: str, pattern: str):
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
    "ID|ARTICLE": capture('ARTICLE', r"\d+(?:\.\d+)?[a-zA-Z]?(?:[-:][a-zA-Z0-9]+)?") + r"(?:{WS}{LITERAL|SUBPARAGRAPH}{WS}{ID|SUBPARAGRAPH})?",

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
        {ID|ARTICLE}
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

_PATTERNS_EXACT_CACHE: List[re.Pattern] | None = None

def get_patterns(mapping, exact=False):
    global _PATTERNS_EXACT_CACHE
    """
    Generate a list of compiled regular expression patterns from a base set,
    with placeholders replaced using the provided mapping.

    The base patterns (from PT_REFS and optionally PT_REFS_EXACT) may contain
    placeholders in the form {placeholder_name}, which are recursively substituted.

    If `exact` is True, each pattern is wrapped to match the entire line (with optional
    leading/trailing whitespace).
    """

    if exact and _PATTERNS_EXACT_CACHE is not None:
        return _PATTERNS_EXACT_CACHE

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

    if exact:
        _PATTERNS_EXACT_CACHE = compiled_patterns

    return compiled_patterns

def fix_matches(matches: list):
    """
    This function describes and executes business logic exceptions to defined
    rules.
    """

    for i in range(len(matches)):
        match = matches[i]

        """
        case 1: if title is BW and (captured) article contains semicolon, then
                interpret the article as [book]:[article]
                to determine if title is BW, take into account all aliases from
                the query below that do not contian a book identifier:
                SELECT DISTINCT(alias) FROM aliases WHERE ref IN (SELECT ref FROM aliases WHERE alias = 'BW');
        """

        if ':' in match['patterns'].get('ARTICLE', '') and \
            (match['patterns'].get('TITLE', '').lower() in ['bw', 'burgerlijk wetboek']) or \
            re.match(r"^bw boek \d+", match['patterns'].get('TITLE', ''), re.I):

            book, art = match['patterns']['ARTICLE'].split(':')
            matches[i]['patterns']['ARTICLE'] = art
            matches[i]['patterns']['BOOK'] = book

    return matches

def match_patterns_regex(text: str, aliases: Union[List[tuple], None] = None):
    """
    If aliases is None: assume that the whole of text is the reference searching for
    If aliases is not None: assume list of possible aliases and search against that
    If aliases is not None but empty: attempted to find aliases but no aliases to find against so return []
    """
    if aliases is not None and len(aliases) == 0:
        return []

    patterns = None
    if aliases is not None and len(aliases) > 0:
        pt_titles = capture("TITLE", "|".join(re.escape(str(title)) for title in aliases))
        patterns = get_patterns({**PT_ATOMS, "TITLE": pt_titles}, False)
    else:
        # TODO, this version of the patterns can be cached
        patterns = get_patterns(PT_ATOMS, True)

    results = []


    for pattern in patterns:
        for match in re.finditer(pattern, text):
            span = match.span()
            if any(r['span']==span for r in results): # ensure single result per span
                continue
            patterns = match.groupdict()
            if not "TITLE" in patterns:
                continue
            results.append({
                "span": span,
                "literal": match.group(0),
                "patterns": match.groupdict()
            })

    return results
