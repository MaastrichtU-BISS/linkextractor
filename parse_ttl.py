import io
import gzip
from rdflib import Graph, Literal
from pyoxigraph import RdfFormat, parse, pyoxigraph
import re
import sqlite3

from time import perf_counter
from contextlib import contextmanager

from collections import defaultdict


class TimerCollector:
    def __init__(self):
        self.timings = {}

    @contextmanager
    def timed(self, label):
        start = perf_counter()
        yield
        end = perf_counter()
        self.timings.setdefault(label, []).append(end - start)

    def report(self):
        for label, times in self.timings.items():
            avg = sum(times) / len(times)
            total = sum(times)
            print(f"[{label}] runs: {len(times)}, avg: {avg:.6f}s, total: {total:.6f}s")

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

def parse_turtle_chunk_1(buffer):
    g = Graph(store="Oxigraph")
    g.parse(data=turtle_head+buffer, format="ox-turtle")

    subject = None
    predicates = {}

    for s, p, o in g:
        subj = str(s)
        if subject is None:
            subject = subj.value

        pred = str(p)
        if isinstance(o, Literal):
            obj = str(o.value)
        else:
            obj = str(o)

        predicates.setdefault(pred, []).append(obj)

    return subject, predicates

def parse_turtle_chunk(buffer):
    parsed = parse(input=turtle_head+buffer, format=RdfFormat.TURTLE,)
    
    subject = None
    predicates = {}

    for s, p, o, _ in parsed:
        subj = str(s)
        if subject is None:
            subject = subj
        
        pred = p.value
        obj = o.value

        predicates.setdefault(pred, []).append(obj)

    return subject, predicates

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
    assert all(key in lawelement and lawelement[key] is not None for key in ['type', 'bwb_id', 'lido_id', 'title'])
    
    cursor.execute("INSERT OR IGNORE INTO lawelement (type, bwb_id, lido_id, jc_id, number, title) VALUES (?, ?, ?, ?, ?, ?);",
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
RE_ECLI_FROM_LIDO_ID = re.compile(r"\/terms\/jurisprudentie\/id\/(.*?)$")

regelingonderdelen = {
    'http://linkeddata.overheid.nl/terms/Wet': 'wet',
    'http://linkeddata.overheid.nl/terms/Deel': 'deel',
    'http://linkeddata.overheid.nl/terms/Boek': 'boek',
    'http://linkeddata.overheid.nl/terms/Titeldeel': 'titeldeel',
    'http://linkeddata.overheid.nl/terms/Hoofdstuk': 'hoofdstuk',
    'http://linkeddata.overheid.nl/terms/Artikel': 'artikel',
    'http://linkeddata.overheid.nl/terms/Paragraaf': 'paragraaf',
    'http://linkeddata.overheid.nl/terms/SubParagraaf': 'subparagraaf',
    'http://linkeddata.overheid.nl/terms/Afdeling': 'afdeling',
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
    le["lido_id"] = node["subject"]
    le["title"] = node['predicates'].get('http://purl.org/dc/terms/title', [None])[0]
    if le["title"] is None:
        le["title"] = node['predicates'].get('http://www.w3.org/2004/02/skos/core#prefLabel', [None])[0]
    if le["title"] is None:
        le["title"] = node['predicates'].get('http://www.w3.org/2000/01/rdf-schema#label', [None])[0]
    
    le["type"] = type
    le['jc_id'] = None

    jcid = node['predicates'].get('http://linkeddata.overheid.nl/terms/heeftJuriconnect')
    if jcid is not None:
        jci13 = next((x for x in jcid if x[0:6]=='jci1.3'), None)
        if jci13 is not None:
            le['jc_id'] = jci13

    bwb_match = RE_BWB_FROM_LIDO_ID.search(le["lido_id"])
    if bwb_match:
        le['bwb_id'] = bwb_match.group(1)

    onderdeel_nummer = node['predicates'].get('http://linkeddata.overheid.nl/terms/heeftOnderdeelNummer')
    if onderdeel_nummer is not None and len(onderdeel_nummer) == 1:
        le['number'] = onderdeel_nummer[0]

    # print(f"processing the {le['type']} with bwb-id {le['bwb_id']}")
    insert_lawelement(cursor, le)

def insert_case(cursor, case):
    assert all(key in case and case[key] is not None for key in ['ecli_id', 'title'])

    cursor.execute("INSERT OR IGNORE INTO legal_case (ecli_id, title) VALUES (?, ?) ", (case['ecli_id'], case['title'],))
    return cursor.lastrowid

def get_lawelement_by_lido_id(cursor, lido_id):
    if not 'terms/bwb/id' in lido_id:
        return (None, None)

    # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826/1711894/1821-08-01/1821-08-01
    # ['https:', '', 'linkeddata.overheid.nl', 'terms', 'bwb', 'id', 'BWBR0001826', '1711894', '1821-08-01', '1821-08-01']
    
    cursor.execute("SELECT id FROM lawelement WHERE lido_id = ?", (lido_id,))
    result = cursor.fetchone()
    if result:
        return (lido_id, result[0])
    
    # print("not found:", lido_id)
    lido_id_no_dates = "/".join(lido_id.split("/")[0:8])
    # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826/1711894
    cursor.execute("SELECT id FROM lawelement WHERE lido_id LIKE ?", (lido_id_no_dates,))
    result = cursor.fetchone()
    if result:
        return (lido_id, result[0])
    
    lido_id_only_bwb = "/".join(lido_id.split("/")[0:7])
    # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826
    cursor.execute("SELECT id FROM lawelement WHERE lido_id LIKE ?", (lido_id_only_bwb,))
    result = cursor.fetchone()
    if result:
        return (lido_id, result[0])
    
    return (None, None)

def insert_caselaw(cursor, caselaw):
    assert all(key in caselaw and caselaw[key] is not None for key in ['case_id', 'law_id', 'source', 'lido_id'])
    
    cursor.execute("INSERT OR IGNORE INTO case_law (case_id, law_id, source, jc_id, lido_id, opschrift) VALUES (?, ?, ?, ?, ?, ?)",
        (
            caselaw['case_id'],
            caselaw['law_id'],
            caselaw['source'],
            caselaw['lido_id'],
            caselaw.get('jc_id'),
            caselaw.get('opschrift'),
        )
    )

def process_case(cursor, node):
    case = {}

    # case["id"] = node["subject"]
    # identifiers = node['predicates'].get('http://purl.org/dc/terms/identifier')
    # if identifiers is not None:
    #     if len(identifiers) and len:
    #     case["ecli_id"] = node['predicates'].get('http://purl.org/dc/terms/title', [None])[0]

    # ecli_id = RE_ECLI_FROM_LIDO_ID.search(node["subject"])
    # if ecli_id:
    #     case["ecli_id"] = ecli_id.group(1)
    # else:
    #     print("No ecli-id found in: ", node["subject"])
    #     return

    ecli_id = node["subject"].split("/")[-1]
    if not ecli_id or ecli_id[0:4] != "ECLI":
        print("No ecli-id found in: ", node["subject"])
        return
    case["ecli_id"] = ecli_id


    case["title"] = node['predicates'].get('http://purl.org/dc/terms/title', [None])[0]
    if case["title"] is None:
        case["title"] = node['predicates'].get('http://www.w3.org/2000/01/rdf-schema#label', [None])[0]
    if case["title"] is None:
        return

    # print(case)
    case_id = insert_case(cursor, case)
    
    links = node['predicates'].get('http://linkeddata.overheid.nl/terms/linkt', [])
    for link in links:
        # print("LINK", link)
        matched_law_lido_id, law_id = get_lawelement_by_lido_id(cursor, link)
        if law_id is None: continue
        caselaw = {
            'case_id': case_id,
            'law_id': law_id,
            'source': 'lido-linkt',
            'jc_id': None,
            'lido_id': matched_law_lido_id,
            'opschrift': None
        }
        insert_caselaw(cursor, caselaw)

    referenties = node['predicates'].get('http://linkeddata.overheid.nl/terms/refereertAan', [])
    for ref in referenties:
        # linktype=http://linkeddata.overheid.nl/terms/linktype/id/lx-referentie|target=bwb|uri=jci1.3:c:BWBR0005288&boek=5&titeldeel=1&artikel=1&z=2024-01-01&g=2024-01-01|lido-id=http://linkeddata.overheid.nl/terms/bwb/id/BWBR0005288/1723924/1992-01-01/1992-01-01|opschrift=artikel 5:1 BW
        ref_props = dict(item.split('=', 1) for item in ref.split("|"))
        if ref_props.get('lido-id') is not None:
            # print("REF LINK", ref_props.get('lido-id'))
            matched_law_lido_id, law_id = get_lawelement_by_lido_id(cursor, ref_props.get('lido-id'))
            if law_id is None: continue
            caselaw = {
                'case_id': case_id,
                'law_id': law_id,
                'source': 'lido-ref',
                'jc_id': ref_props.get('uri'),
                'lido_id': matched_law_lido_id,
                'opschrift': ref_props.get('opschrift')
            }
            insert_caselaw(cursor, caselaw)

            # if ref_props.get("opschrift") is not None:
            #     insert_alias(cursor, )
    
    # exit(1)


def stream_turtle_chunks(file_path):
    in_multiline_string = False
    buffer = []

    with open_fast_gzip_lines(file_path) as f:
        for line in f:
            buffer.append(line)

            # Count the number of triple quotes to toggle state
            triple_quote_count = line.count('"""') + line.count("'''")
            if triple_quote_count % 2 == 1:
                # Odd number of triple quotes in line - toggle state
                in_multiline_string = not in_multiline_string

            # if not in_multiline_string and line.strip().endswith('.'):
            if not in_multiline_string and len(line) > 1 and line[-2] == ".":
                chunk = ''.join(buffer)
                yield chunk
                buffer.clear()


typeuri = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'

def process_ttl_laws(conn, file_path):
    cursor = conn.cursor()
    # tc = TimerCollector()
    print("Start processing law items")

    parse_err_count = 0
    lawelement_count = 0

    i=0
    for chunk in stream_turtle_chunks(file_path):
        i+=1
        if i % 10000 == 0: print(i, "->", lawelement_count)
        
        # heuristic check if this chunk is relevant for us
        if 'terms/Wet' not in chunk and \
            'terms/Deel' not in chunk and \
            'terms/Boek' not in chunk and \
            'terms/Titeldeel' not in chunk and \
            'terms/Hoofdstuk' not in chunk and \
            'terms/Artikel' not in chunk and \
            'terms/Paragraaf' not in chunk and \
            'terms/SubParagraaf' not in chunk and \
            'terms/Afdeling' not in chunk:
                continue
        
        try:
            # with tc.timed("parse turtle"):
            node = parse_turtle_chunk(chunk)
            if node is None or node['subject'] is None or node['predicates'] is None:
                continue
        except Exception as err:
            print("Parse tripple error", err)
            print("Chunk:", chunk)
            parse_err_count+=1
            # if parse_err_count>=100:
            #     exit(1)
            continue
        
        if typeuri in node['predicates'] and len(node['predicates'][typeuri]) == 1:
            a = node['predicates'][typeuri][0]
            if a in regelingonderdelen:
                lawelement_count += 1
                
                # with tc.timed("process element"):
                process_lawelement(cursor, node, regelingonderdelen[a])

                # with tc.timed("commit to db"):
                if lawelement_count % 2000 == 0:
                    print(f"{lawelement_count}) committing to db...")
                    conn.commit()
    
    conn.commit()
    cursor.close()
    print(f"Finished processing {lawelement_count} law items (with {parse_err_count} parsing errors)")
    # tc.report()


# BEFORE BENCH AND COPY:
# 7500000 -> 674686
# 676000) committing to db...
# 678000) committing to db...
# 680000) committing to db...
# 682000) committing to db...
# 7510000 -> 683597
# 684000) committing to db...
# 686000) committing to db...
# 688000) committing to db...
# 690000) committing to db...

def process_ttl_cases(conn, file_path):
    cursor = conn.cursor()
    # cursor = None

    print("Start processing case items")
    
    tc = TimerCollector()
    parse_err_count = 0
    case_count = 0
    last_case_count = 0

    i = 0
    for chunk in stream_turtle_chunks(file_path):
        i+=1
        
        if i % 50000 == 0:
            delta = case_count - last_case_count
            last_case_count = case_count
            print(i, "->", case_count, f"(+ {delta})" if delta > 0 else "")
        # if i >= 2000000: break
        # if i >=1800: break
        # if i < 6730000: continue
        # if i > 1730000 and i < 6610000: continue

        # with tc.timed("hueristic"):
        # heuristic check if this chunk is relevant for us
        if not 'terms/Jurisprudentie' in chunk:
            continue
        
        # with tc.timed("parse turtle"):
        try:
            subject, predicates = parse_turtle_chunk(chunk)
            if subject is None or predicates == {}:
                continue
        except Exception as err:
            print("Parse tripple error", err)
            raise err
            print("Chunk:", chunk)
            parse_err_count+=1
            if parse_err_count>=100:
                exit(1)
            continue
        
        # print(predicates)
        # break
        if typeuri in predicates and len(predicates[typeuri]) == 1:
            a = predicates[typeuri][0]
            if a == 'http://linkeddata.overheid.nl/terms/Jurisprudentie':
                case_count += 1
                # with tc.timed("process case"):
                process_case(cursor, {'subject': subject, 'predicates': predicates})
                
                # with tc.timed("commiting"):
                if case_count % 2000 == 0:
                    print(f"- {case_count}) *commit*")
                    conn.commit()

    conn.commit()
    cursor.close()
    print(f"Finished processing {case_count} cases (with {parse_err_count} parsing errors)")
    tc.report()

if __name__=="__main__":
    
    # process_ttl_cases(None, "data/dynamic/lido-export.ttl.gz")
    # exit(1)

    with get_conn() as conn:
        # init_db(conn)
        
        path = "data/dynamic/lido-export.ttl.gz"
        
        # process_ttl_laws(conn, path)
        process_ttl_cases(conn, path)

    # process_ttl_gz(conn, "data/dynamic/lido-export.ttl.gz")

    # Total number of sentences in turtle file is about: 19752995 (
    #   19752995 in python,
    #   19752982 in python without rstrip () (211.73s)
    #   19752969 with zcat and grep " \.$"")

    # Total number of 'law items', given the list regelingonderdelen
    # ...

    # Benchmarks                              n           t (s)
    # ---------------------------    ----------   -------------
    # w/o print, w/o strip (all)     19_752_982             211
    # before with print i                10_000              15.8 (5.5s system)
    # before without print               10_000               4.7
    # buffered reader print i            10_000               0.9
    # buffered reader w/o print i        10_000               0.3
    # buffered reader print i           100_000              11.3
    # buffered reader w/o print i       100_000               7.1 then 4.9
    
    # parse for law items               100_000              56
    # parse for law items (all)         888_635            1732.30 (28m)

    # parse w/ graph + insert             4_000              20      200/s
    #                                   184_000             560.83   320/s
    #
    # parsed count cases              3_575_771            2635.12

    # projection for scanning all articles    19752982 = 3.07h
