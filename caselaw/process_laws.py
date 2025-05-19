
import sys
from caselaw.constants import RE_BWB_FROM_LIDO_ID, REGELING_ONDERDELEN, TERM_URI_TYPE
from caselaw.utils.print import printerr
from caselaw.utils.stream import stream_triples, stream_turtle_chunks
from caselaw.utils.turtle import parse_turtle_chunk


def insert_law_element(cursor, law_element):
    assert all(key in law_element and law_element[key] is not None for key in ['type', 'bwb_id', 'lido_id', 'title'])
    
    cursor.execute("INSERT OR IGNORE INTO law_element (type, bwb_id, lido_id, jc_id, number, title) VALUES (?, ?, ?, ?, ?, ?);",
        (
            law_element['type'], 
            law_element['bwb_id'],
            law_element['lido_id'],
            law_element.get('jc_id'),
            law_element.get('number'),
            law_element.get('title'),
            # law_element['title'],
        )
    )

def strip_lido_law_id(lido_law_id):
    if lido_law_id[0:43] == "http://linkeddata.overheid.nl/terms/bwb/id/" and len(lido_law_id) > 43:
        return lido_law_id[43:]
    return None

def process_law_element(cursor, type, subject, predicates):
                        
    #   id INTEGER PRIMARY KEY,
    # -- parent_id INTEGER,
    #   bwb_id INTEGER,
    # x  lidoid TEXT UNIQUE,
    # x  jcid TEXT NOT NULL UNIQUE,
    #   number TEXT,
    # x type TEXT,
    # x title TEXT,
    #   alt_title TEXT,
    #   FOREIGN KEY (parent_id) REFERENCES law_element(id)

    le = {}

    le["type"] = "law"

    # http://linkeddata.overheid.nl/terms/bwb/id/BWBR0001831/799354/1827-12-13/1827-12-13
    stripped_id = strip_lido_law_id(subject)
    if stripped_id is None:
        printerr("Item with subject", subject, "has incorrect format")
        return False
    
    le["lido_id"] = stripped_id

    bwb_match = le["lido_id"].split("/")[0]
    if bwb_match:
        le['bwb_id'] = bwb_match
    else:
        printerr("No BWB-id for subject:", subject)
        return False

    le["title"] = predicates.get('http://purl.org/dc/terms/title', [None])[0]
    if le["title"] is None:
        le["title"] = predicates.get('http://www.w3.org/2004/02/skos/core#prefLabel', [None])[0]
    if le["title"] is None:
        le["title"] = predicates.get('http://www.w3.org/2000/01/rdf-schema#label', [None])[0]
    
    le["type"] = type
    le['jc_id'] = None

    jcid = predicates.get('http://linkeddata.overheid.nl/terms/heeftJuriconnect')
    if jcid is not None:
        jci13 = next((x for x in jcid if x[0:6]=='jci1.3'), None) # first jc
        if jci13 is not None:
            le['jc_id'] = jci13

    onderdeel_nummer = predicates.get('http://linkeddata.overheid.nl/terms/heeftOnderdeelNummer')
    if onderdeel_nummer is not None and len(onderdeel_nummer) == 1:
        le['number'] = onderdeel_nummer[0]

    # print(f"processing the {le['type']} with bwb-id {le['bwb_id']}")
    insert_law_element(cursor, le)

def process_ttl_laws(conn, filename):
    
    cursor = conn.cursor()

    i = 0
    last_law_count = 0
    law_count = 0
    err_count = 0

    print("Start processing law items (2)")

    for subject, props in stream_triples(filename):
        try:
            i+=1
            
            if i % 50000 == 0:
                delta = law_count - last_law_count
                last_law_count = law_count
                print("-", i, "->", law_count, f"(+ {delta})" if delta > 0 else "")

            type = props.get(TERM_URI_TYPE, [None])[0]
            if type is not None and type in REGELING_ONDERDELEN:
                law_count += 1
                
                # with tc.timed("process element"):
                process_law_element(cursor, REGELING_ONDERDELEN[type], subject, props)
                # process_case_block(cursor, subject, props)

                # with tc.timed("commit to db"):
                if law_count % 50000 == 0:
                    print(" ", i, "->", law_count, "*commit*")
                    conn.commit()
            elif type is not None:
                pass
                # printerr(f"Uncaught type {type} for subject {subject}")
        
        except Exception as err:
            printerr("** Error:", err)
            printerr("** i, subject, props:", i, subject,"\n")
            err_count+=1
            if err_count>=100:
                printerr("Max error count exceeded. Raising error.")
                raise err
            continue

    
    conn.commit()
    cursor.close()
    print(f"Finished processing {law_count} law elements (with {err_count} errors)")

def process_ttl_laws_old(conn, file_path):
    cursor = conn.cursor()
    # tc = TimerCollector()
    print("Start processing law items")

    parse_err_count = 0
    law_element_count = 0

    i=0
    for chunk in stream_turtle_chunks(file_path):
        i+=1
        if i % 10000 == 0: print(i, "->", law_element_count)
        
        # if i > 1_000_000:
        #     break
        
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
            subject, predicates = parse_turtle_chunk(chunk)
            if subject is None or predicates == {}:
                continue
        except Exception as err:
            print("Parse tripple error", err)
            print("Chunk:", chunk)
            raise err
            parse_err_count+=1
            # if parse_err_count>=100:
            #     exit(1)
            continue
        
        if TERM_URI_TYPE in predicates and len(predicates[TERM_URI_TYPE]) == 1:
            a = predicates[TERM_URI_TYPE][0]
            if a in REGELING_ONDERDELEN:
                law_element_count += 1
                
                # with tc.timed("process element"):
                process_law_element(cursor, REGELING_ONDERDELEN[a], subject, predicates)

                # with tc.timed("commit to db"):
                if law_element_count % 2000 == 0:
                    print(f"{law_element_count}) committing to db...")
                    conn.commit()
    
    conn.commit()
    cursor.close()
    print(f"Finished processing {law_element_count} law items (with {parse_err_count} parsing errors)")
    # tc.report()

