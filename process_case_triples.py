
# --
from pyoxigraph import RdfFormat, parse
from collections import defaultdict
import sys

from pipeline.process_cases import get_law_element_by_lido_id

def insert_case(cursor, case):
    assert all(key in case and case[key] is not None for key in ['ecli_id', 'title'])

    cursor.execute("INSERT OR IGNORE INTO legal_case (ecli_id, title, ) VALUES (?, ?) ", (case['ecli_id'], case['title'],))
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


def process_case_block1(subject, props):
    # print(props)
    if 'link_linkt' in props:
        print(subject, len(props['link_linkt']))
    # print(subject)
    # for k, v in props.items():
    #     print("\t", k, "->", v)
    return

def process_case_block(cursor, subject, props):
    case = {}

    ecli_id = props.get('ecli_id', [None])[0] # approach one to get ecli
    if not ecli_id or ecli_id[0:4] != "ECLI":
        ecli_id = subject.split("/")[-1]      # approach two to get ecli
    if not ecli_id or ecli_id[0:4] != "ECLI":
        print("No ecli-id found in subject:", subject)
        return
    case["ecli_id"] = ecli_id


    # case["title"] = props['title_1'] or props['title_2'] or props['title_3'] or []
    case["title"] = props.get('title_1', props.get('title_2', props.get('title_3', [None])))[0]
    if case["title"] is None:
        print("No title for subject:", subject)
        return

    # print(case)
    case_id = insert_case(cursor, case)
    
    links = props.get('link_linkt', [])
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

    referenties = props.get('link_ref', [])
    for ref in referenties:
        # linktype=http://linkeddata.overheid.nl/terms/linktype/id/lx-referentie|target=bwb|uri=jci1.3:c:BWBR0005288&boek=5&titeldeel=1&artikel=1&z=2024-01-01&g=2024-01-01|lido-id=http://linkeddata.overheid.nl/terms/bwb/id/BWBR0005288/1723924/1992-01-01/1992-01-01|opschrift=artikel 5:1 BW
        ref_props = dict(item.split('=', 1) for item in ref.split("|"))
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

map_terms = {
    'http://purl.org/dc/terms/identifier': 'ecli_id',
    'http://purl.org/dc/terms/type': 'dct_type',
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': 'lido_type',
    'http://purl.org/dc/terms/title': 'title_1',
    'http://www.w3.org/2000/01/rdf-schema#label': 'title_2',
    'http://www.w3.org/2004/02/skos/core#prefLabel': 'title_3',
    'http://linkeddata.overheid.nl/terms/refereertAan': 'link_ref',
    'http://linkeddata.overheid.nl/terms/linkt': 'link_linkt',
    'http://linkeddata.overheid.nl/terms/heeftUitspraakdatum': 'datum_uitspraak',
    'http://linkeddata.overheid.nl/terms/heeftZaaknummer': 'zaaknummer',
}

def parse_subject_block(triples):
    """
    triples: list of raw N-Triples lines (strings) for a single subject
    Returns: list of (predicate, object) pairs
    """
    nt_block = "\n".join(triples)
    parsed = list(parse(nt_block.encode(), format=RdfFormat.N_TRIPLES))
    # print(parsed)
    d = defaultdict(list)
    for t in parsed:
        d[map_terms[t.predicate.value]].append(t.object.value)
    return dict(d)
    # return [(t.predicate.value, t.object.value) for t in parsed]
    # return {map_terms[t.predicate.value]: t.object for t in parsed}


current_subject = None
subject_props = None

def process(filename):
    current_subject = None
    current_lines = []
    i = 0

    with open(filename, "r", buffering=1 << 20) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Extract subject string from line (manually, fast)
            if line.startswith('<'):
                subj_end = line.find('>')
                subject = line[1:subj_end]
            else:
                continue  # skip malformed line

            # skip empty
            if len(subject) <= 54:
                continue

            # New subject boundary?
            if subject != current_subject:
                if current_subject is not None and current_lines:
                    i+=1
                    if i % 100_000 == 0: print(i)

                    props = parse_subject_block(current_lines)
                    process_case_block(current_subject, props)

                # Reset for new subject
                current_subject = subject
                current_lines = []

            current_lines.append(line)

        if current_subject and current_lines:
            props = parse_subject_block(current_lines)
            process_case_block(current_subject, props)

if __name__ == "__main__":
    process("./data/dynamic/lido-cases-sort.nt")