import gzip
# from rdflib import Graph
# from rdflib.parser import Parser
# from rdflib.plugins.parsers.ntriples import W3CNTriplesParser
import re
import sqlite3


# pre‑compiled regexes from before
split_predicates = re.compile(r'\s*;\s*')
split_objects    = re.compile(r'\s*,\s*')
literal_value    = re.compile(r'^"(?P<val>.*)"(?:\^\^<(?P<dtype>[^>]+)>)?$')

def parse_turtle_chunk(buffer: str) -> dict:
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
                lit = {"lit": m.group("val")}
                if m.group("dtype"):
                    lit["dtype"] = m.group("dtype")
                objs.append(lit)
            else:
                objs.append(o)

        result["predicates"].setdefault(pred_token, []).extend(objs)

    return result


LITERAL_RE = re.compile(r'^"(?P<val>.*)"(?:\^\^<(?P<dtype>[^>]+)>)?$')
def parse_turtle_chunk_uhh(buf: str):
    """
    Turn one full subject–predicate block (no trailing '.') into:
      subject, predicates_dict
    where predicates_dict maps predicate → list of objects.
    """
    # 1) strip trailing period and whitespace
    buf = buf.strip()
    if buf.endswith('.'):
        buf = buf[:-1].rstrip()

    # 2) split off subject
    subject, sep, rest = buf.partition(' ')
    predicates = {}

    # 3) split predicate blocks on semicolon
    for seg in rest.split(';'):
        seg = seg.strip()
        if not seg:
            continue

        # split pred from objs
        pred, sep, objs_str = seg.partition(' ')
        if not sep:
            continue  # no objects

        # split objects on comma
        objs = []
        for o in objs_str.split(','):
            o = o.strip()
            m = LITERAL_RE.match(o)
            if m:
                lit = m.group("val")
                dtype = m.group("dtype")
                objs.append({'lit': lit, 'dtype': dtype} if dtype else {'lit': lit})
            else:
                objs.append(o)

        # accumulate
        predicates.setdefault(pred, []).extend(objs)

    return subject, predicates

# Connect to PostgreSQL
conn = sqlite3.connect("database.db")

# ---

# cursor = conn.cursor()
# # Create table if needed (customize types and columns)
# cursor.execute("""
#     CREATE TABLE IF NOT EXISTS rdf_data (
#         subject TEXT,
#         predicate TEXT,
#         object TEXT
#     );
# """)
# conn.commit()
# cursor.close()

# ---

def triple_filter(subj, predicate, obj):
    if predicate not in ['http://linkeddata.overheid.nl/terms/refereertAan', 'http://linkeddata.overheid.nl/terms/linkt']:
        return
    print(subj, predicate, obj)
    # return "somePredicate" in str(pred)

def insert(cursor, subj, predicate, obj):
    return
    cursor.execute("INSERT INTO rdf_data VALUES (%s, %s, %s);",
        (str(subj), str(predicate), str(obj)))

def process_ttl_gz(file_path):
    i = 0

    # cursor = conn.cursor()
    
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        buffer = ''
        for line in f:
            buffer += line
            if line.strip().endswith('.'):
                i += 1
                print(i)

                if (i > 10000):
                    break

                continue

                node = {}
                try:
                    node = parse_turtle_chunk(buffer)
                except:
                    print(buffer)
                    exit()
                
                buffer = ''

                if 'a' in node['predicates'] and len(node['predicates']) == 1:
                    a = node['predicates']['a'][0]

                    if a == '<http://linkeddata.overheid.nl/terms/Artikel>':
                        pass
                    elif a == '<http://linkeddata.overheid.nl/terms/Jurisprudentie>':
                        print(i, node['subject'], node['predicates']['a'])
                    else:
                        pass


                # try:
                #     # Parse the triple
                #     temp_graph = Graph()
                #     temp_graph.parse(data=turtle_head+buffer, format='turtle')
                #     for s, p, o in temp_graph:
                #         if triple_filter(s, p, o):
                #             insert(cursor, s, p, o)
                #     buffer = ''
                # except Exception as e:
                #     print("Parse error:", e)
                #     buffer = ''  # Reset on error
    
    # conn.commit()
    # cursor.close()

process_ttl_gz("data/dynamic/lido-export.ttl.gz")
# Total number of sentences in turtle file is about: 19752995 (19752995 in python, 19752969 with zcat and grep " \.$"")
conn.close()