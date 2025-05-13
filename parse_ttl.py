import io
import gzip
from rdflib import Graph, Literal
from rdflib.parser import Parser
from rdflib.plugins.parsers.ntriples import W3CNTriplesParser
import re
import sqlite3

split_predicates = re.compile(r'\s*;\s*')
split_objects    = re.compile(r'\s*,\s*')
literal_value    = re.compile(r'^"(?P<val>.*)"(?:\^\^<(?P<dtype>[^>]+)>)?$')

def parse_turtle_chunk_aa(buffer: str) -> dict:
    buf = buffer.strip()
    if buf.endswith('.'):
        buf = buf[:-1].strip()

    parts = buf.split(None, 1)
    subject = parts[0]
    rest    = parts[1] if len(parts) == 2 else ''
    result = {"subject": subject, "predicates": {}}

    # split into predicate-object segments
    segments = split_predicates.split(rest)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        # guard: require at least one whitespace to separate pred from objs
        seg_parts = seg.split(None, 1)
        if len(seg_parts) != 2:
            # nothing to do here—skip
            continue

        pred_token, objs_str = seg_parts
        objs = []
        for o in split_objects.split(objs_str):
            o = o.strip()
            m = literal_value.match(o)
            if m:
                lit = m.group('val')
                objs.append(lit)
            else:
                objs.append(o)

        result["predicates"].setdefault(pred_token, []).extend(objs)

    return result

turtle_head = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sesame: <http://www.openrdf.org/schema/sesame#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix fn: <http://www.w3.org/2005/xpath-functions#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix hint: <http://www.bigdata.com/queryHints#> .
@prefix bd: <http://www.bigdata.com/rdf#> .
@prefix bds: <http://www.bigdata.com/rdf/search#> .

"""

def parse_turtle_chunk(buffer):
    g = Graph()
    g.parse(data=turtle_head+buffer, format="turtle")

    result = {"subject": None, "predicates": {}}

    for s, p, o in g:
        subj = str(s)
        if result["subject"] is None:
            result["subject"] = subj

        pred = str(p)
        if isinstance(o, Literal):
            # lit = {"lit": o.value}
            # if o.datatype:
            #     lit["dtype"] = str(o.datatype)
            # obj = lit

            obj = str(o.value)
        else:
            obj = str(o)

        result["predicates"].setdefault(pred, []).append(obj)

    return result

# Connect to PostgreSQL
def get_conn():
    return sqlite3.connect("caselaw.db")


def init_db(conn):
    print("Initializing database")
    cursor = conn.cursor()
    # Create table if needed (customize types and columns)
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS legal_case (
            id INTEGER PRIMARY KEY,
            ecli_id TEXT UNIQUE,
            title TEXT
        );
        
        CREATE TABLE IF NOT EXISTS lawelement (
            id INTEGER PRIMARY KEY,
            -- parent_id INTEGER,
            type TEXT CHECK (type IN ('wet', 'boek', 'deel', 'titeldeel', 'hoofdstuk', 'artikel', 'paragraaf', 'subparagraaf', 'afdeling')),
            bwb_id INTEGER,
            lido_id TEXT UNIQUE,
            jc_id TEXT UNIQUE,
            number TEXT,
            title TEXT,
            alt_title TEXT
            -- FOREIGN KEY (parent_id) REFERENCES lawelement(id)
        );

        CREATE TABLE IF NOT EXISTS law_alias (
            id INTEGER PRIMARY KEY,
            lawelement_id INTEGER,
            alias TEXT,
            source TEXT,
            FOREIGN KEY (lawelement_id) REFERENCES lawelement(id)
        );

        CREATE TABLE IF NOT EXISTS case_law (
            id INTEGER PRIMARY KEY,
            case_id INTEGER,
            law_id INTEGER,
            source TEXT CHECK (source IN ('lido-ref', 'lido-linkt', 'custom')),
            jc_id TEXT,
            lido_id TEXT,
            opschrift TEXT,
            FOREIGN KEY (case_id) REFERENCES legal_case(id),
            FOREIGN KEY (law_id) REFERENCES lawelement(id)
        );
    """)
    conn.commit()
    cursor.close()
    print("Database initialized.")

def insert_lawelement(cursor, lawelement):
    assert all(key in lawelement for key in ['type', 'bwb_id', 'lido_id', 'title'])
    
    cursor.execute("INSERT INTO lawelement (type, bwb_id, lido_id, jc_id, number, title) VALUES (?, ?, ?, ?, ?, ?);",
        (
            lawelement['type'], 
            lawelement['bwb_id'],
            lawelement['lido_id'],
            lawelement.get('jc_id'),
            lawelement.get('number'),
            lawelement.get('title'),
            # lawelement['title'],
        )
    )

def open_fast_gzip_lines(path):
    f = gzip.open(path, 'rb')  # binary mode
    buffered = io.BufferedReader(f, buffer_size=1024 * 1024)  # 1MB buffer
    # return io.TextIOWrapper(buffered, encoding='utf-8', errors='ignore')
    return io.TextIOWrapper(buffered, encoding='utf-8')

RE_BWB_FROM_LIDO_ID = re.compile(r"\/terms\/bwb\/id\/(.*?)\/")

regelingonderdelen = {
    '<http://linkeddata.overheid.nl/terms/Wet>': 'wet',
    '<http://linkeddata.overheid.nl/terms/Boek>': 'boek',
    '<http://linkeddata.overheid.nl/terms/Deel>': 'deel',
    '<http://linkeddata.overheid.nl/terms/Titeldeel>': 'titeldeel',
    '<http://linkeddata.overheid.nl/terms/Hoofdstuk>': 'hoofdstuk',
    '<http://linkeddata.overheid.nl/terms/Artikel>': 'artikel',
    '<http://linkeddata.overheid.nl/terms/Paragraaf>': 'paragraaf',
    '<http://linkeddata.overheid.nl/terms/SubParagraaf>': 'subparagraaf',
    '<http://linkeddata.overheid.nl/terms/Afdeling>': 'afdeling',
}

def process_lawelement(cursor, node, type):
                        
    #   id INTEGER PRIMARY KEY,
    # -- parent_id INTEGER,
    #   bwb_id INTEGER,
    # x  lidoid TEXT UNIQUE,
    # x  jcid TEXT NOT NULL UNIQUE,
    #   number TEXT,
    # x type TEXT,
    # x title TEXT,
    #   alt_title TEXT,
    #   FOREIGN KEY (parent_id) REFERENCES lawelement(id)

    le = {}

    le["type"] = "law"
    le["lido_id"] = node["subject"].strip('<>')
    le["title"] = node['predicates'].get('<http://purl.org/dc/terms/title>', [None])[0]
    
    le["type"] = type

    juriconnect = node['predicates'].get('<http://linkeddata.overheid.nl/terms/heeftJuriconnect>')
    if juriconnect is not None:
        jci13 = next((x for x in juriconnect if x[0:5]=='jci1.3'), None)
        if jci13 is not None:
            le['jc_id'] = jci13

    bwb_match = RE_BWB_FROM_LIDO_ID.search(le["lido_id"])
    if bwb_match:
        le['bwb_id'] = bwb_match.group(1)

    onderdeel_nummer = node['predicates'].get('<http://linkeddata.overheid.nl/terms/heeftOnderdeelNummer>')
    if onderdeel_nummer is not None and len(onderdeel_nummer) == 1:
        node['number'] = onderdeel_nummer[0]

    print(f"processing the {le['type']} with bwb-id {le['bwb_id']}")
    insert_lawelement(cursor, le)

def process_case(cursor, node):
    case = {}

    print(i, a, "->", node['subject'], "\n")
    
    # case["type"] = "case"
    case["id"] = node["subject"].strip("<>")
    case["title"] = node['predicates'].get('<http://purl.org/dc/terms/title>', [None])[0]

    insert_case()

    referenties = node['predicates'].get('<http://linkeddata.overheid.nl/terms/refereertAan>', [None])
    # https://linkeddata.overheid.nl/terms/jurisprudentie/id/ECLI:NL:RBLIM:2025:3601
    for ref in referenties:
        # linktype=http://linkeddata.overheid.nl/terms/linktype/id/lx-referentie|target=bwb|uri=jci1.3:c:BWBR0005288&boek=5&titeldeel=1&artikel=1&z=2024-01-01&g=2024-01-01|lido-id=http://linkeddata.overheid.nl/terms/bwb/id/BWBR0005288/1723924/1992-01-01/1992-01-01|opschrift=artikel 5:1 BW
        ref_props = dict(item.split('=') for item in ref_props.split("|"))
        if ref_props.get('target') == 'bwb' and ref_props.get('uri') is not None:
            get_law_by_jci()

            insert_link(x, y, 'lido-ref')

            if ref_props.get("opschrift") is not None:
                insert_opschrift()

def process_ttl_gz(conn, file_path):
    cursor = conn.cursor()
    
    # First: import all law-elements
    # Then: process all links (by processing cases)

    print("Start processing law items")

    counter = 0
    with open_fast_gzip_lines(file_path) as f:
        buffer = []
        for line in f:
            buffer.append(line)
            # if line.rstrip().endswith('.'):
            if len(line) > 1 and line[-2] == ".":
                chunk = ''.join(buffer)
                buffer.clear()

                node = {}
                try:
                    node = parse_turtle_chunk(chunk)
                    if node is None or node['subject'] is None or node['predicates'] is None:
                        continue
                    print("parsed", node)
                except Exception as err:
                    print("Parse tripple error", err)
                    print("Chunk:", chunk)
                    exit(1)

                if 'a' in node['predicates'] and len(node['predicates']['a']) == 1:
                    a = node['predicates']['a'][0]
                    print(a)
                    break
                    if a in regelingonderdelen:
                        counter += 1
                        process_lawelement(cursor, node, regelingonderdelen[a])
            
                        if counter % 2000 == 0:
                            print(f"{counter}) committing to db...")
                            conn.commit()

                if counter >= 2000: break
                continue
    
    print(f"Finished processing {counter} law items")
    quit()
    return

    print("Start processing case items")

    counter = 0
    with open_fast_gzip_lines(file_path) as f:
        buffer = []
        for line in f:
            buffer.append(line)
            # if line.rstrip().endswith('.'):
            if len(line) > 1 and line[-2] == ".":

                chunk = ''.join(buffer)
                buffer.clear()

                node = {}
                try:
                    node = parse_turtle_chunk(chunk)
                except Exception as err:
                    print("Parse tripple error", err)
                    exit()

                if 'a' in node['predicates'] and len(node['predicates']['a']) == 1:

                    if a == '<http://linkeddata.overheid.nl/terms/Jurisprudentie>':
                        counter += 1
                        process_case(cursor, node)

            if counter > 100000: break
            continue

    # print(i)
    conn.commit()
    # cursor.close()

if __name__=="__main__":
    conn = get_conn()
    init_db(conn)
    process_ttl_gz(conn, "data/dynamic/lido-export.ttl.gz")


    # Total number of sentences in turtle file is about: 19752995 (
    #   19752995 in python,
    #   19752982 in python without rstrip () (211.73s)
    #   19752969 with zcat and grep " \.$"")

    # Total number of 'law items', given the list regelingonderdelen
    # ...

    # Benchmarks                      n         t (s)
    # ---------------------------     -----     -------------------
    # w/o print, w/o strip (all)      19752982  211s
    # before with print i             10000     15.8 (5.5s system)
    # before without print            10000     4.7
    # buffered reader print i         10000     0.9
    # buffered reader w/o print i     10000     0.3
    # buffered reader print i         100000    11.3
    # buffered reader w/o print i     100000    7.1 then 4.9
    
    # parse for law items             100000    56s
    # parse for law items (all)       888635    1732.30s (28m)

    # projection for scanning all articles    19752982 = 3.07h 



