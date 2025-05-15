import sys

from caselaw.constants import TERM_URI_TYPE
from caselaw.process_laws import strip_lido_law_id
from caselaw.utils.benchmarking import TimerCollector
from caselaw.utils.stream import stream_turtle_chunks
from caselaw.utils.turtle import parse_turtle_chunk


def get_lawelement_by_lido_id(cursor, lido_id):
    # if not 'terms/bwb/id' in lido_id:
    #     return (None, None)
    stripped_id = strip_lido_law_id(lido_id)
    if stripped_id is None: # could be due to being ref to ecli
        return (None, None)

    # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826/1711894/1821-08-01/1821-08-01
    # ['https:', '', 'linkeddata.overheid.nl', 'terms', 'bwb', 'id', 'BWBR0001826', '1711894', '1821-08-01', '1821-08-01']
    
    cursor.execute("SELECT id FROM lawelement INDEXED BY sqlite_autoindex_lawelement_1 WHERE lido_id = ? LIMIT 1", (stripped_id,))
    result = cursor.fetchone()
    if result:
        return (stripped_id, result[0])
    
    # print("not found:", lido_id)
    lido_id_no_dates = "/".join(stripped_id.split("/")[0:2])
    # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826/1711894
    cursor.execute("SELECT id FROM lawelement INDEXED BY sqlite_autoindex_lawelement_1 WHERE lido_id LIKE ? LIMIT 1", (lido_id_no_dates,))
    result = cursor.fetchone()
    if result:
        return (stripped_id, result[0])
    
    lido_id_only_bwb = "/".join(lido_id.split("/")[0:1])
    # https://linkeddata.overheid.nl/terms/bwb/id/BWBR0001826
    cursor.execute("SELECT id FROM lawelement INDEXED BY sqlite_autoindex_lawelement_1 WHERE lido_id LIKE ? LIMIT 1", (lido_id_only_bwb,))
    result = cursor.fetchone()
    if result:
        return (lido_id, result[0])
    
    return (None, None)

def insert_case(cursor, case):
    assert all(key in case and case[key] is not None for key in ['ecli_id', 'title'])

    cursor.execute("INSERT OR IGNORE INTO legal_case (ecli_id, title) VALUES (?, ?) ", (case['ecli_id'], case['title'],))
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

def process_case(cursor, subject, predicates):
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

    ecli_id = subject.split("/")[-1]
    if not ecli_id or ecli_id[0:4] != "ECLI":
        print("No ecli-id found in: ", subject)
        return
    case["ecli_id"] = ecli_id


    case["title"] = predicates.get('http://purl.org/dc/terms/title', [None])[0]
    if case["title"] is None:
        case["title"] = predicates.get('http://www.w3.org/2000/01/rdf-schema#label', [None])[0]
    if case["title"] is None:
        return

    # print(case)
    case_id = insert_case(cursor, case)
    
    links = predicates.get('http://linkeddata.overheid.nl/terms/linkt', [])
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

    referenties = predicates.get('http://linkeddata.overheid.nl/terms/refereertAan', [])
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

# #  
# - 2236000) *commit*
# - 2238000) *commit*
# - 2240000) *commit*
# - 2242000) *commit*
# 9150000 -> 2243466 
# - 2244000) *commit*
# - 2246000) *commit*
# - 2248000) *commit*

def process_ttl_cases(conn, file_path):
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
                    if case_count % 2000 == 0:
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
