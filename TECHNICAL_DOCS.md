# LinkExtractor Technical Documentation

## Table of Contents
1. [Overview](#1-overview)
2. [Architecture & Module Breakdown](#2-architecture--module-breakdown)
3. [Input Handling](#3-input-handling)
4. [Branching Logic](#4-branching-logic)
5. [Algorithms & Extraction Logic](#5-algorithms--extraction-logic)
6. [Output Formats](#6-output-formats)
7. [Error Handling & Edge Cases](#7-error-handling--edge-cases)
8. [Configuration & Extensibility](#8-configuration--extensibility)
9. [Example Workflows](#9-example-workflows)
10. [API & CLI Usage](#10-api--cli-usage)

---

## 1. Overview

### Purpose

LinkExtractor is a Python package designed to extract legal reference links from text documents. It specializes in identifying and resolving references to Dutch law (wetgeving), including articles, books, and legal codes such as the Burgerlijk Wetboek (BW), Algemene wet bestuursrecht (AWB), and others.

### Supported Input Types

The system supports two primary input types:

1. **Full-Text Documents**: Large documents containing multiple legal references embedded within natural language text. These require alias detection and pattern matching across the entire document.

2. **Exact/Small Literal Inputs**: Short strings that represent a single, complete legal reference (e.g., "Art. 7:658 BW"). These are processed with the assumption that the entire input is the reference.

### High-Level Workflow

```
Input Text
    │
    ▼
┌─────────────────────────────────┐
│   Mode Detection (exact flag)   │
└─────────────────────────────────┘
    │                    │
    ▼                    ▼
[Exact Mode]        [In-Text Mode]
    │                    │
    │                    ▼
    │          ┌─────────────────────┐
    │          │ Alias Detection     │
    │          │ (Trie or Database)  │
    │          └─────────────────────┘
    │                    │
    ▼                    ▼
┌─────────────────────────────────┐
│      Pattern Matching           │
│   (Regex-based extraction)      │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│      Match Post-Processing      │
│   (fix_matches, normalization)  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│      Database Law Resolution    │
│   (find_laws, alias lookup)     │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│         Result Assembly         │
└─────────────────────────────────┘
    │
    ▼
Output (List of Link dictionaries)
```

### Main Components

| Component | File | Description |
|-----------|------|-------------|
| CLI/Main Entry | `main.py` | Command-line interface and orchestration |
| Core Extraction | `search.py` | Main `extract_links()` function |
| Pattern Definitions | `patterns.py` | Regex patterns for legal references |
| Database Access | `db.py` | PostgreSQL connection management |
| Utility Functions | `utils.py` | Alias search, law resolution, trie management |
| Type Definitions | `types.py` | TypedDict definitions for type safety |
| Analysis Tools | `analyze/` | Development tools for accuracy analysis |

---

## 2. Architecture & Module Breakdown

### Core Modules

#### `linkextractor/__init__.py`
- **Responsibility**: Package initialization and public API exposure
- **Exports**: `extract_links` function from `search.py`

#### `linkextractor/search.py`
- **Responsibility**: Core link extraction logic
- **Key Functions**:
  - `extract_links(text, exact=False, loose=False, use_trie=True)`: Main extraction entry point
- **Interactions**:
  - Calls `patterns.py` for regex matching
  - Calls `utils.py` for alias detection and law resolution
  - Returns structured link results

#### `linkextractor/patterns.py`
- **Responsibility**: Define and compile regex patterns for legal references
- **Key Functions**:
  - `get_atoms()`: Returns atomic pattern components (cached)
  - `get_patterns(titles=None)`: Compiles full regex patterns for matching
  - `match_patterns_regex(text, aliases)`: Executes pattern matching against text
  - `fix_matches(matches)`: Post-processes matches for special cases (e.g., BW book:article notation)
  - `capture(name, pattern)`: Helper for named capture groups
  - `sub_pattern_placeholders(pattern, mapping)`: Recursive placeholder substitution

#### `linkextractor/utils.py`
- **Responsibility**: Database queries and alias management
- **Key Functions**:
  - `get_trie()`: Loads or builds marisa-trie for fast alias lookup
  - `find_aliases_in_text(text, use_trie)`: Finds law aliases in text
  - `find_longest_alias_in_substring(input_text)`: Finds longest matching alias
  - `find_matching_aliases(name, wildcard)`: Database alias search with wildcards
  - `find_laws(fragments, alias, bwb_id)`: Resolves fragments to specific law elements

#### `linkextractor/db.py`
- **Responsibility**: Database connection management
- **Key Functions**:
  - `get_conn()`: Returns PostgreSQL connection using psycopg2
  - `set_db_url(url)`: Override default database URL
- **Configuration**: Uses `LINKEXTRACTOR_DB_URL` environment variable

#### `linkextractor/types.py`
- **Responsibility**: Type definitions for structured data
- **Key Types**:
  - `Resource`: Law resource with `title`, `bwb_id`, `bwb_label_id`
  - `Fragment`: Reference fragments with `boek`, `artikel`
  - `Link`: Complete link with `resource` and `fragment`
  - `Alias`: Mapping of `bwb_id` to `alias`

#### `linkextractor/main.py`
- **Responsibility**: CLI entry point and argument parsing
- **Key Functions**:
  - `main()`: Parses arguments, dispatches to appropriate handlers
- **Commands**: `eval`, `test`, `analyze`

#### `linkextractor/permutations.py`
- **Responsibility**: Generate test permutations (development tool)
- **Note**: Not part of main functionality; used for testing pattern coverage

### Analysis Modules (`linkextractor/analyze/`)

#### `analyze/prepare.py`
- **Responsibility**: Prepare test samples from database
- **Key Functions**:
  - `prepare(sample_size, seed)`: Generate random sample of cases
  - `prepare_specific(ecli_id)`: Download specific case for analysis

#### `analyze/method_1.py`
- **Responsibility**: Compare extraction results against LIDO ground truth
- **Key Functions**:
  - `analyze()`: Run full comparison analysis
  - `compare_links(links_true, links_test)`: Compute TP/FP/FN metrics

#### `analyze/method_2.py`
- **Responsibility**: Alternative analysis using indicator patterns
- **Key Functions**:
  - `analyze_2()`: Indicator-based analysis
  - `get_indicator_spans(text)`: Find potential reference indicators

### Package Dependencies

```
linkextractor
├── lxml            # XML/HTML parsing
├── requests        # HTTP client
├── pytest          # Testing framework
├── pyoxigraph      # RDF graph database
├── rdflib          # RDF library
├── psycopg2-binary # PostgreSQL adapter
├── python-dotenv   # Environment variable loading
└── marisa-trie     # Fast trie data structure
```

---

## 3. Input Handling

### Distinguishing Full-Text vs. Exact Inputs

The system uses the `exact` parameter to differentiate between input types:

| Parameter | Input Type | Behavior |
|-----------|------------|----------|
| `exact=False` | Full-text document | Scans for aliases, finds multiple references |
| `exact=True` | Exact string | Treats entire input as single reference |

### Processing by Input Type

#### Full-Text Processing (`exact=False`)

1. **Alias Detection**: Scans the text for known law aliases
   - Uses Trie for fast prefix matching (when `use_trie=True`)
   - Falls back to database `LIKE` queries (when `use_trie=False`)
2. **Pattern Generation**: Builds regex patterns incorporating found aliases
3. **Multi-Match Extraction**: Finds all matching references in text

#### Exact Processing (`exact=True`)

1. **No Alias Pre-Detection**: Skips alias scanning
2. **Full Pattern Matching**: Uses all patterns including exact-only patterns
3. **Whole-String Matching**: Patterns are wrapped with `^\s*...\s*$`
4. **Single Result Expected**: Warns if multiple results found

### Preprocessing and Normalization

- **Whitespace Handling**: Patterns use flexible whitespace matching (`\s*`, `\s+`)
- **Case Insensitivity**: All patterns compiled with `re.IGNORECASE`
- **Text Truncation for Logging**: Long texts truncated to 128 chars for debug output

### Length and Format Heuristics

The system does not use explicit length thresholds. Instead:
- The `exact` flag is set by the caller based on context
- Exact patterns (`PT_REFS_EXACT`) are simpler and match minimal reference formats
- Full-text patterns (`PT_REFS`) are more structured requiring article literals

---

## 4. Branching Logic

### Major Processing Branches

#### Branch 1: Exact Mode → Direct Pattern Matching

**Trigger**: `exact=True` parameter

**Codepath**:
```python
extract_links(text, exact=True)
    → aliases = None (skip alias detection)
    → match_patterns_regex(text, aliases=None)
        → get_patterns() returns PT_REFS + PT_REFS_EXACT
        → patterns wrapped with ^\s*...\s*$
    → fix_matches(matches)
    → find_laws() for each match
```

**Expected Output**: Single result or warning for multiple matches

#### Branch 2: Full-Text Mode → Alias Detection + Pattern Matching

**Trigger**: `exact=False` parameter (default)

**Codepath**:
```python
extract_links(text, exact=False)
    → find_aliases_in_text(text, use_trie)
        → [Trie path] get_trie().prefixes()
        → [DB path] SQL LIKE query + word boundary check
    → match_patterns_regex(text, aliases)
        → get_patterns(titles=joined_aliases)
        → patterns search for specific alias matches
    → fix_matches(matches)
    → Split multi-article matches (ARTICLES → individual ARTICLE)
    → find_laws() for each match
```

**Expected Output**: List of all found references with spans

#### Branch 3: Loose Mode → Fallback to Alias-Only Results

**Trigger**: `loose=True` and no pattern matches found

**Codepath**:
```python
if len(matches) == 0 and loose:
    → Use aliases directly as matches
    → Create synthetic match entries with TITLE=alias
    → find_laws() for each alias
```

**Expected Output**: Matches based on alias presence only (lower precision)

#### Branch 4: Trie vs. Database Alias Lookup

**Trigger**: `use_trie` parameter

| use_trie | Path |
|----------|------|
| `True` | Load/build marisa-trie from file or DB, prefix matching |
| `False` | Direct SQL `LIKE` query with word boundary validation |

#### Branch 5: BW Book:Article Notation Fix

**Trigger**: Article contains `:` and title is "BW" or "Burgerlijk Wetboek"

**Codepath**:
```python
fix_matches(matches):
    if ':' in article and title.lower() in ['bw', 'burgerlijk wetboek']:
        → Split "7:658" into book="7", article="658"
        → Update match patterns
```

**Expected Output**: Properly separated book and article fragments

#### Branch 6: Multi-Article Reference Splitting

**Trigger**: Match contains `ARTICLES` capture group (multiple references)

**Codepath**:
```python
if 'ARTICLES' in match['patterns']:
    → Split by conjunction pattern (jo., en, comma)
    → Create sub_match for each individual article
    → Process each sub_match separately
```

**Expected Output**: Multiple result entries from single match

#### Branch 7: Fallback Alias Resolution

**Trigger**: No laws found for matched alias

**Codepath**:
```python
if len(laws) == 0:
    → find_longest_alias_in_substring(match['patterns']['TITLE'])
    → find_laws(fragments, bwb_id=longest_alias['bwb_id'])
```

**Expected Output**: Resolves partial alias matches to full law

---

## 5. Algorithms & Extraction Logic

### Pattern Matching System

The system uses a hierarchical regex pattern structure:

#### Atomic Patterns (`PT_ATOMS`)

Building blocks for constructing full patterns:

| Atom | Pattern | Description |
|------|---------|-------------|
| `WS_0` | `\s*` | Zero or more whitespace |
| `WS` | `\s+` | One or more whitespace |
| `COMMA_SPACE` | `(?:[,]\s*\|\s+)` | Comma or space separator |
| `LITERAL\|BOOK` | `(?:boek\|bk\.?)` | Book literal variants |
| `LITERAL\|ARTICLE` | `(?:artikel(?:en)?\|artt?\.?)` | Article literal variants |
| `LITERAL\|CONJUNCTION` | `(?:\s+jo.\|\s+en\|\s*,)` | Reference conjunctions |
| `ID\|BOOK` | `(?P<BOOK>[0-9]+)` | Book number capture |
| `ID\|ARTICLE` | `(?P<ARTICLE>\d+(?:\.\d+)?[a-zA-Z]?...)` | Article ID capture |
| `TITLE` | `(?P<TITLE>.+?)` | Law title capture |

#### Reference Patterns (`PT_REFS`)

Full patterns for in-text matching:

1. **Structured with Book**: `Artikel 5 van het boek 7 van het BW`
2. **Simple Article+Title**: `Artikel 61 Wet toezicht trustkantoren 2018`
3. **Title-First**: `Burgerlijk Wetboek Boek 7, Artikel 658`
4. **Multiple Articles**: `Artikel 7:658 van het BW`

#### Exact-Only Patterns (`PT_REFS_EXACT`)

Additional patterns for exact string matching:

1. **Minimal Reference**: `3:2 awb` (no article literal required)

### Alias Detection Algorithm

#### Trie-Based Detection

```python
def find_aliases_in_text(text, use_trie=True):
    trie = get_trie()
    norm_text = text.lower()
    results = []
    for i in range(len(norm_text)):
        matches = trie.prefixes(norm_text[i:])
        if matches:
            alias = max(matches, key=len)  # Longest match
            results.append(alias)
    return results
```

- **Complexity**: O(n * m) where n=text length, m=max alias length
- **Optimization**: Trie cached after first load

#### Database-Based Detection

```python
SELECT DISTINCT alias FROM law_alias
WHERE lower(%s) LIKE '%' || lower(alias) || '%'
LIMIT 50;
```

- Followed by word boundary validation with regex
- **Trade-off**: More accurate but slower than Trie

### Law Resolution Algorithm

```python
def find_laws(fragments, alias=None, bwb_id=None):
    # 1. Order fragments by specificity
    fragment_tuples = sorted(fragments, key=type_order)
    
    # 2. Query law_element table
    # - Match all fragment (type, number) pairs
    # - Filter by alias or bwb_id
    # - Return narrowest matching elements
```

Fragment ordering (broad to narrow):
`wet → boek → deel → titeldeel → hoofdstuk → artikel → paragraaf → afdeling`

### Supported Citation Formats

| Format Type | Example |
|-------------|---------|
| Abbreviated Article | `Art. 7:658 BW` |
| Full Article | `Artikel 7:658 Burgerlijk Wetboek` |
| With Prepositions | `Artikel 7:658 van het BW` |
| Book Explicit | `Artikel 658 van boek 7 van het BW` |
| Title First | `Burgerlijk Wetboek Boek 7, Artikel 658` |
| Minimal (exact) | `3:2 awb` |
| With Subparagraph | `Art. 5:1 lid 2 BW` |
| Multiple Articles | `artt. 1 en 2 BW` |
| Decimal Articles | `Artikel 7.28 WHW` |
| Suffixed Articles | `Artikel 7.57H WHW` |

### Pipeline Stages

1. **Tokenization**: Implicit via regex matching
2. **Normalization**: Case normalization, whitespace flexibility
3. **Detection**: Pattern matching with capture groups
4. **Validation**: Database lookup confirms law existence
5. **Formatting**: Result assembly with context information

---

## 6. Output Formats

### Standard Output Structure

The `extract_links()` function returns a list of dictionaries:

```python
[
    {
        'context': {
            'span': (start_index, end_index),  # Position in source text
            'literal': 'matched text string'    # Exact matched text
        },
        'resource': {
            'title': 'Full law title',
            'bwb_id': 'BWBR0005290',            # BWB identifier
            'bwb_label_id': 'numeric_id'        # Label identifier
        },
        'fragment': {
            'artikel': '658',                   # Article number
            'boek': '7',                        # Book number (optional)
            'subparagraaf': '2'                 # Subparagraph (optional)
        }
    }
]
```

### Output Differences by Branch

| Mode | Context.span | Context.literal | Fragment detail |
|------|--------------|-----------------|-----------------|
| Exact | May be (None, None) | Full input | Single reference |
| In-Text | (start, end) | Matched substring | May be multiple |
| Loose | Computed position | Alias text | Minimal |

### Type Definitions

```python
class Resource(TypedDict):
    title: str           # Full law title
    bwb_id: str          # BWB reference ID
    bwb_label_id: NotRequired[str]

class Fragment(TypedDict):
    boek: NotRequired[str]      # Book number
    artikel: NotRequired[str]   # Article number

class Link(TypedDict):
    resource: Resource
    fragment: NotRequired[Fragment]
```

### CLI Output

When using the CLI, results are printed to stdout:
```
{'context': {'span': (0, 15), 'literal': 'Art. 7:658 BW'}, 'resource': {...}, 'fragment': {...}}
```

### Optional Metadata Fields

| Field | When Present |
|-------|--------------|
| `bwb_label_id` | When law element found in database |
| `boek` | When book number is specified |
| `subparagraaf` | When lid/subparagraph is specified |

---

## 7. Error Handling & Edge Cases

### Error Handling Strategies

#### Database Connection Errors

- Connection timeout set to 5 seconds
- No retry logic; exceptions propagate to caller
- Environment variable `LINKEXTRACTOR_DB_URL` must be set

#### No Matches Found

- Returns empty list `[]`
- No exception raised
- Debug logging indicates "no patterns found"

#### Multiple Results in Exact Mode

```python
if exact and len(results) > 1:
    logging.warning("more than one result found for exact search")
```

- Warning logged but all results returned
- Caller should handle ambiguity

### Edge Cases

#### Missing Metadata

| Scenario | Behavior |
|----------|----------|
| No BWB label ID | Result included without `bwb_label_id` |
| No book number | `fragment.boek` omitted |
| Alias not in DB | Falls back to substring match |

#### Very Short Inputs

- Exact mode handles short references like `3:2 awb`
- Minimum viable: article identifier + title alias

#### Unsupported Citation Styles

- European regulations (e.g., `Verordening (EG) nr. 1618/1999`) not matched
- Non-Dutch legal systems not supported
- Returns empty list for unrecognized formats

#### Mixed-Format References

- `Artt. 1 en 2 BW` → Split into multiple results
- `art. 2:346 lid 1, aanhef en onder e BW` → Captured as complex article ID

### Fallback Logic

1. **Primary**: Pattern match with alias
2. **Fallback 1**: Substring alias search
3. **Fallback 2**: Loose mode (if enabled) - alias as match
4. **Final**: Empty result list

### Validation and Filtering

- **Span Deduplication**: Same span not repeated in results
- **Fragment Uniqueness**: Same span+fragment combination not duplicated
- **Word Boundary Check**: Database aliases validated against word boundaries

---

## 8. Configuration & Extensibility

### Configuration Options

#### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `LINKEXTRACTOR_DB_URL` | PostgreSQL connection string | None (required) |

#### Runtime Flags

| Flag | CLI Option | Effect |
|------|------------|--------|
| `exact` | `-e/--exact` | Enable exact matching mode |
| `use_trie` | `-n/--no-trie` | Disable trie for alias lookup |
| `verbose` | `-v/--verbose` | Enable debug logging |
| `database` | `-d/--database` | Override database URL (takes precedence over `LINKEXTRACTOR_DB_URL`) |

### Files

| File | Purpose |
|------|---------|
| `aliases.trie` | Cached marisa-trie for fast alias lookup |
| `.env` | Environment variables (via python-dotenv) |

### Extending the System

#### Adding New Extraction Rules

1. **Add Atomic Patterns** in `patterns.py`:
```python
PT_ATOMS["NEW_LITERAL"] = r"(?:new|pattern)"
```

2. **Add Reference Pattern** in `PT_REFS`:
```python
r'''
    {NEW_LITERAL}
    {WS}
    {ID|ARTICLE}
    {WS}
    {TITLE}
'''
```

3. **Add Post-Processing** in `fix_matches()` if needed

#### Adding New Input Types

1. **Create New Mode Flag** in `extract_links()`
2. **Add Conditional Logic** for alias detection
3. **Create Mode-Specific Patterns** if needed

#### Adding New Output Formats

1. **Extend Type Definitions** in `types.py`
2. **Modify Result Assembly** in `search.py`
3. **Update CLI Output** in `main.py`

### Safe Extension Points

| Location | Extension Type | Risk Level |
|----------|---------------|------------|
| `PT_ATOMS` | New atomic patterns | Low |
| `PT_REFS` | New reference patterns | Medium |
| `fix_matches()` | Post-processing rules | Medium |
| `types.py` | New type definitions | Low |
| `main.py` | New CLI commands | Low |

### Database Schema Dependencies

The system expects these tables:

| Table | Key Columns |
|-------|-------------|
| `law_alias` | `alias`, `bwb_id` |
| `law_element` | `bwb_id`, `bwb_label_id`, `type`, `number`, `title` |
| `legal_case` | `id`, `ecli_id` |
| `case_law` | `law_id`, `case_id`, `source`, `opschrift` |

---

## 9. Example Workflows

### Example 1: Full Research Article → Multiple Extractions

**Input**:
```python
text = """
De rechtbank oordeelt dat artikel 7:658 van het BW van toepassing is.
Tevens is artikel 3:2 Algemene wet bestuursrecht relevant voor deze zaak.
"""
results = extract_links(text, exact=False)
```

**Processing Path**:
1. Alias detection finds: `['bw', 'algemene wet bestuursrecht']`
2. Pattern matching finds 2 matches
3. Each match resolved against database
4. Results assembled with span information

**Output**:
```python
[
    {
        'context': {'span': (30, 60), 'literal': 'artikel 7:658 van het BW'},
        'resource': {'title': 'Burgerlijk Wetboek Boek 7', 'bwb_id': 'BWBR0005290', ...},
        'fragment': {'artikel': '658', 'boek': '7'}
    },
    {
        'context': {'span': (80, 125), 'literal': 'artikel 3:2 Algemene wet bestuursrecht'},
        'resource': {'title': 'Algemene wet bestuursrecht', 'bwb_id': 'BWBR0005537', ...},
        'fragment': {'artikel': '3:2'}
    }
]
```

### Example 2: Short Snippet → Single Citation (Exact Mode)

**Input**:
```python
results = extract_links("Art. 5:1 lid 2 BW", exact=True)
```

**Processing Path**:
1. Skip alias detection (exact mode)
2. Pattern matches against `PT_REFS + PT_REFS_EXACT`
3. BW title triggers book:article split in `fix_matches()`
4. Database lookup confirms law element

**Output**:
```python
[
    {
        'context': {'span': (0, 17), 'literal': 'Art. 5:1 lid 2 BW'},
        'resource': {'title': 'Burgerlijk Wetboek Boek 5', 'bwb_id': 'BWBR0005288', ...},
        'fragment': {'artikel': '1', 'boek': '5', 'subparagraaf': '2'}
    }
]
```

### Example 3: No References Found

**Input**:
```python
results = extract_links("Dit is een tekst zonder juridische verwijzingen.", exact=False)
```

**Processing Path**:
1. Alias detection finds no matches
2. `match_patterns_regex` returns early (empty aliases)
3. Empty result list returned

**Output**:
```python
[]
```

### Example 4: Ambiguous/Conflicting Patterns

**Input**:
```python
results = extract_links("BW", exact=True)
```

**Processing Path**:
1. Exact mode pattern matching
2. No article/book identifiers found
3. Pattern requires article literal → no match

**Output**:
```python
[]  # "BW" alone is not a complete reference
```

### Example 5: Multiple Articles in Single Reference

**Input**:
```python
text = "Artikelen 1, 2 en 3 van het BW"
results = extract_links(text, exact=False)
```

**Processing Path**:
1. Pattern matches with `ARTICLES` capture group
2. Split by conjunction pattern
3. Three sub-matches created
4. Each resolved separately

**Output**:
```python
[
    {'fragment': {'artikel': '1'}, ...},
    {'fragment': {'artikel': '2'}, ...},
    {'fragment': {'artikel': '3'}, ...}
]
```

---

## 10. API & CLI Usage

### Python API

#### Basic Usage

```python
from linkextractor import extract_links

# Full-text extraction
results = extract_links(
    "Artikel 7:658 van het BW is van toepassing.",
    exact=False,      # Scan for multiple references
    use_trie=True     # Use trie for fast alias lookup
)

# Exact string extraction
results = extract_links(
    "Art. 7:658 BW",
    exact=True        # Treat entire input as single reference
)
```

#### Function Signature

```python
def extract_links(
    text: str,           # Input text to search
    exact: bool = False, # Exact match mode
    loose: bool = False, # Fallback to alias-only matches
    use_trie: bool = True # Use trie for alias detection
) -> List[Dict]:
    """
    Extract legal reference links from text.
    
    Returns:
        List of dictionaries with keys:
        - 'context': {'span': tuple, 'literal': str}
        - 'resource': {'title': str, 'bwb_id': str, 'bwb_label_id': str}
        - 'fragment': {'artikel': str, 'boek': str, ...}
    """
```

#### Return Type

```python
List[Dict[str, Any]]
# Each dict contains:
# {
#     'context': {
#         'span': Tuple[int, int],  # Start and end positions
#         'literal': str            # Matched text
#     },
#     'resource': {
#         'title': str,             # Law title
#         'bwb_id': str,            # BWB identifier
#         'bwb_label_id': str       # Optional label ID
#     },
#     'fragment': {
#         'artikel': str,           # Article number
#         'boek': str,              # Book number (optional)
#         'subparagraaf': str       # Subparagraph (optional)
#     }
# }
```

### CLI Usage

#### Installation

```bash
# Install from source
pip install -e .

# Or install dependencies
pip install -r requirements.txt
```

#### Commands

##### `eval` - Evaluate Text

```bash
# Exact match from argument
linkextractor eval -e "Art. 7:658 BW"

# Full-text from argument
linkextractor eval "Dit betreft artikel 7:658 BW."

# From stdin
echo "Art. 7:658 BW" | linkextractor eval -e

# With options
linkextractor eval -e -n "Art. 7:658 BW"  # Disable trie
linkextractor eval -v "text"               # Verbose output
linkextractor eval -d "postgres://..." "text"  # Custom database
```

##### `test` - Run Test Queries

```bash
# Run predefined test queries with benchmarking
linkextractor test
linkextractor test -v  # Verbose output
```

##### `analyze` - Analysis Pipeline

```bash
# Prepare samples from database
linkextractor analyze -p              # Default: 10 samples
linkextractor analyze -p -n 100       # 100 samples
linkextractor analyze -p -s 42        # With seed
linkextractor analyze -p -c "ECLI:..." # Cherry-pick specific case

# Run analysis
linkextractor analyze               # Method 1: Compare with LIDO
linkextractor analyze -2            # Method 2: Indicator analysis
```

### Integration Examples

#### Django Integration

```python
from linkextractor import extract_links

def process_legal_document(document_text):
    references = extract_links(document_text, exact=False)
    
    for ref in references:
        LegalReference.objects.create(
            document=document,
            bwb_id=ref['resource']['bwb_id'],
            article=ref['fragment'].get('artikel'),
            span_start=ref['context']['span'][0],
            span_end=ref['context']['span'][1]
        )
```

#### FastAPI Endpoint

```python
from fastapi import FastAPI
from linkextractor import extract_links

app = FastAPI()

@app.post("/extract")
async def extract_references(text: str, exact: bool = False):
    return extract_links(text, exact=exact)
```

#### Batch Processing

```python
from linkextractor import extract_links
import json

def process_documents(documents):
    results = []
    for doc in documents:
        refs = extract_links(doc['text'], exact=False)
        results.append({
            'doc_id': doc['id'],
            'references': refs
        })
    return results
```

### Environment Setup

```bash
# Required environment variable
export LINKEXTRACTOR_DB_URL="postgresql://user:pass@host:5432/dbname"

# Or use .env file
echo 'LINKEXTRACTOR_DB_URL="postgresql://user:pass@host:5432/dbname"' > .env
```

### Testing

```bash
# Run pytest test suite
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/exact/test_bw.py
```

---

## Appendix: Database Schema Reference

### Required Tables

```sql
-- Law aliases table
CREATE TABLE law_alias (
    id SERIAL PRIMARY KEY,
    alias VARCHAR NOT NULL,
    bwb_id VARCHAR NOT NULL
);

-- Law elements table
CREATE TABLE law_element (
    id SERIAL PRIMARY KEY,
    bwb_id VARCHAR NOT NULL,
    bwb_label_id INTEGER,
    type VARCHAR NOT NULL,
    number VARCHAR,
    title VARCHAR
);

-- Legal cases table
CREATE TABLE legal_case (
    id SERIAL PRIMARY KEY,
    ecli_id VARCHAR NOT NULL UNIQUE
);

-- Case-law relationship table
CREATE TABLE case_law (
    id SERIAL PRIMARY KEY,
    law_id INTEGER REFERENCES law_element(id),
    case_id INTEGER REFERENCES legal_case(id),
    source VARCHAR,
    opschrift VARCHAR
);
```

### Indexes for Performance

```sql
CREATE INDEX idx_law_alias_alias ON law_alias(lower(alias));
CREATE INDEX idx_law_alias_bwb_id ON law_alias(bwb_id);
CREATE INDEX idx_law_element_type_number ON law_element(type, lower(number));
CREATE INDEX idx_law_element_bwb_id ON law_element(bwb_id);
```
