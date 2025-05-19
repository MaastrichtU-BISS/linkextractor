from collections import defaultdict
import sys

from pyoxigraph import RdfFormat, parse

from caselaw.constants import TERM_URI_TYPE
from caselaw.process_laws import strip_lido_law_id
from caselaw.utils.benchmarking import TimerCollector
from caselaw.utils.stream import stream_triples, stream_turtle_chunks
from caselaw.utils.turtle import parse_turtle_chunk


def get_law_element_by_lido_id(cursor, lido_id):
    # if not 'terms/bwb/id' in lido_id:
    #     return (None, None)
    stripped_id = strip_lido_law_id(lido_id)
    if stripped_id is None: # could be due to being ref to ecli
        return (None, None)

    # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826/1711894/1821-08-01/1821-08-01
    # ['https:', '', 'linkeddata.overheid.nl', 'terms', 'bwb', 'id', 'BWBR0001826', '1711894', '1821-08-01', '1821-08-01']
    
    cursor.execute("SELECT id FROM law_element INDEXED BY sqlite_autoindex_law_element_1 WHERE lido_id = ? LIMIT 1", (stripped_id,))
    result = cursor.fetchone()
    if result:
        return (stripped_id, result[0])
    
    # # print("not found:", lido_id)
    # lido_id_no_dates = "/".join(stripped_id.split("/")[0:2])
    # # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826/1711894
    # cursor.execute("SELECT id FROM law_element INDEXED BY sqlite_autoindex_law_element_1 WHERE lido_id LIKE ? LIMIT 1", (lido_id_no_dates,))
    # result = cursor.fetchone()
    # if result:
    #     return (stripped_id, result[0])
    
    # lido_id_only_bwb = "/".join(lido_id.split("/")[0:1])
    # # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826
    # cursor.execute("SELECT id FROM law_element INDEXED BY sqlite_autoindex_law_element_1 WHERE lido_id LIKE ? LIMIT 1", (lido_id_only_bwb,))
    # result = cursor.fetchone()
    # if result:
    #     return (lido_id, result[0])
    
    return (None, None)

def insert_case(cursor, case):
    assert all(key in case and case[key] is not None for key in ['ecli_id'])

    cursor.execute("INSERT OR IGNORE INTO legal_case (ecli_id, title, zaaknummer, uitspraakdatum) VALUES (?, ?, ?, ?) ", 
                   (case['ecli_id'], case.get('title'), case.get('zaaknummer'), case.get('uitspraakdatum'),))
    return cursor.lastrowid

def insert_caselaw(cursor, caselaw):
    assert all(key in caselaw and caselaw[key] is not None for key in ['case_id', 'law_id', 'source', 'lido_id'])
    
    cursor.execute("INSERT OR IGNORE INTO case_law (case_id, law_id, source, jc_id, lido_id, opschrift) VALUES (?, ?, ?, ?, ?, ?)",
        (
            caselaw['case_id'],
            caselaw['law_id'],
            caselaw['source'],
            caselaw.get('jc_id'),
            caselaw['lido_id'],
            caselaw.get('opschrift'),
        )
    )

# map_terms = {
#     'http://purl.org/dc/terms/identifier': 'ecli_id',
#     'http://purl.org/dc/terms/type': 'dct_type',
#     'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': 'lido_type',
#     'http://purl.org/dc/terms/title': 'title_1',
#     'http://www.w3.org/2000/01/rdf-schema#label': 'title_2',
#     'http://www.w3.org/2004/02/skos/core#prefLabel': 'title_3',
#     'http://linkeddata.overheid.nl/terms/refereertAan': 'link_ref',
#     'http://linkeddata.overheid.nl/terms/linkt': 'link_linkt',
#     'http://linkeddata.overheid.nl/terms/heeftUitspraakdatum': 'datum_uitspraak',
#     'http://linkeddata.overheid.nl/terms/heeftZaaknummer': 'zaaknummer',
# }

def process_case_block(cursor, subject, props):
    case = {}

    # props = {map_terms[k]: v for k, v in props.items()}

    ecli_id = subject.split("/")[-1]              # approach one to get ecli
    # if not ecli_id or ecli_id[0:4] != "ECLI":
    #     ecli_id = props.get('ecli_id', [None])[0] # approach two to get ecli
    if not ecli_id or ecli_id[0:4] != "ECLI":
        print("No ecli-id found in subject:", subject)
        return
    case["ecli_id"] = ecli_id

    # case["title"] = props['title_1'] or props['title_2'] or props['title_3'] or []
    case["title"] = props.get('http://purl.org/dc/terms/title',
                        props.get('http://www.w3.org/2000/01/rdf-schema#label',
                            props.get('http://www.w3.org/2004/02/skos/core#prefLabel', [None])))[0]

    case["zaaknummer"] = props.get("http://linkeddata.overheid.nl/terms/heeftZaaknummer", [None])[0]
    case["uitspraakdatum"] = props.get("http://linkeddata.overheid.nl/terms/heeftUitspraakdatum", [None])[0]

    # print(case)
    case_id = insert_case(cursor, case)
    if case_id is None:
        raise Exception("NO CASE ID!", subject)
    
    links = props.get('http://linkeddata.overheid.nl/terms/linkt', [])
    for link in links:
        # print("LINK", link)
        matched_law_lido_id, law_id = get_law_element_by_lido_id(cursor, link)
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

    referenties = props.get('http://linkeddata.overheid.nl/terms/refereertAan', [])
    for ref in referenties:
        # linktype=http://linkeddata.overheid.nl/terms/linktype/id/lx-referentie|target=bwb|uri=jci1.3:c:BWBR0005288&boek=5&titeldeel=1&artikel=1&z=2024-01-01&g=2024-01-01|lido-id=http://linkeddata.overheid.nl/terms/bwb/id/BWBR0005288/1723924/1992-01-01/1992-01-01|opschrift=artikel 5:1 BW
        ref_props = dict(((item.split("=", 1) + [None])[:2]) for item in ref.split("|")) # <- split first on pipe, then on equal (=) max 2, then pad right with None
        if ref_props.get('lido-id') is not None:
            # print("REF LINK", ref_props.get('lido-id'))
            matched_law_lido_id, law_id = get_law_element_by_lido_id(cursor, ref_props.get('lido-id'))
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

# map_terms = {
#     'http://purl.org/dc/terms/identifier': 'ecli_id',
#     'http://purl.org/dc/terms/type': 'dct_type',
#     'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': 'lido_type',
#     'http://purl.org/dc/terms/title': 'title_1',
#     'http://www.w3.org/2000/01/rdf-schema#label': 'title_2',
#     'http://www.w3.org/2004/02/skos/core#prefLabel': 'title_3',
#     'http://linkeddata.overheid.nl/terms/refereertAan': 'link_ref',
#     'http://linkeddata.overheid.nl/terms/linkt': 'link_linkt',
#     'http://linkeddata.overheid.nl/terms/heeftUitspraakdatum': 'datum_uitspraak',
#     'http://linkeddata.overheid.nl/terms/heeftZaaknummer': 'zaaknummer',
# }

def parse_subject_block(triple_block):
    """
    triples: list of raw N-Triples lines (strings) for a single subject
    Returns: list of (predicate, object) pairs
    """
    parsed = list(parse(triple_block.encode(), format=RdfFormat.N_TRIPLES))
    # print(parsed)
    d = defaultdict(list)
    for t in parsed:
        d[map_terms[t.predicate.value]].append(t.object.value)
    return dict(d)
    # return [(t.predicate.value, t.object.value) for t in parsed]
    # return {map_terms[t.predicate.value]: t.object for t in parsed}

def process_ttl_cases(conn, filename):
    
    cursor = conn.cursor()

    i = 0
    case_count = 0
    last_case_count = 0
    err_count = 0

    print("Start processing case items (2)")

    for subject, props in stream_triples(filename):
        try:
            case_count+=1
            
            # if case_count % 50000 == 0:
            #     delta = case_count - last_case_count
            #     last_case_count = case_count
            #     print("-", case_count, f"(+ {delta})" if delta > 0 else "")

            process_case_block(cursor, subject, props)
            
            # with tc.timed("commiting"):
            if case_count % 50000 == 0:
                delta = case_count - last_case_count
                print(" ", case_count, "*commit*")
                conn.commit()
        
        except Exception as err:
            print("** Error:", err, file=sys.stderr)
            print("** i, subject, props:", i, subject,"\n", props, file=sys.stderr)
            err_count+=1
            if err_count>=100:
                print("Max error count exceeded. Raising error.")
                raise err
            continue
    
    conn.commit()
    cursor.close()
    print(f"Finished processing {case_count} cases (with {err_count} errors)")

def process_ttl_cases_OLD(conn, file_path):
    cursor = conn.cursor()
    # cursor = None

    print("Start processing case items")
    
    # tc = TimerCollector()
    err_count = 0
    case_count = 0
    last_case_count = 0

    i = 0
    for chunk in stream_turtle_chunks(file_path):
        try:
            i+=1
            
            if i % 50000 == 0:
                delta = case_count - last_case_count
                last_case_count = case_count
                print("-", i, "->", case_count, f"(+ {delta})" if delta > 0 else "")

            # if i >= 2_000_000: break
            # if i >=1800: break
            # if i < 6_800_000: continue
            # if i > 7_000_000: break
            # if i > 1730000 and i < 6610000: continue

            # with tc.timed("hueristic"):
            # heuristic check if this chunk is relevant for us
            if not 'terms/Jurisprudentie' in chunk:
                continue
            
            # with tc.timed("parse turtle"):
            subject, predicates = parse_turtle_chunk(chunk)
            if subject is None or predicates == {}:
                continue
            
            if TERM_URI_TYPE in predicates and len(predicates[TERM_URI_TYPE]) == 1:
                a = predicates[TERM_URI_TYPE][0]
                if a == 'http://linkeddata.overheid.nl/terms/Jurisprudentie':
                    case_count += 1
                    # with tc.timed("process case"):
                    process_case(cursor, subject, predicates)
                    
                    # with tc.timed("commiting"):
                    if case_count % 50000 == 0:
                        delta = case_count - last_case_count
                        print(" ", i, "->", case_count, "*commit*")
                        conn.commit()
        
        except Exception as err:
            print("** Error:", err, file=sys.stderr)
            print("** Chunk of error:", chunk, file=sys.stderr)
            err_count+=1
            if err_count>=100:
                print("Max error count exceeded. Raising error.")
                raise err
            continue
    
    conn.commit()
    cursor.close()
    print(f"Finished processing {case_count} cases (with {err_count} errors)")
    # tc.report()
