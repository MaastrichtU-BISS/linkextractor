from collections import Counter
import logging
import os
import json
from src.search import extract_links
from src.types import Link
from datetime import datetime
import re

DIR_ANALYSIS_DATA = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data_method_2')
FILE_STATS = os.path.join(DIR_ANALYSIS_DATA, "method_2_stats.csv")
FILENAME_CASE_TEXT = "full_text.txt"
FILENAME_CASE_INDICATORS = "links_indicators.json"
FILENAME_CASE_LIDO_LINKS = "links_lido.json"
FILENAME_CASE_ANALYSIS = "analysis_indicators.json"

def get_amount_case_samples():
    amount_case_dirs = 0
    with os.scandir(DIR_ANALYSIS_DATA) as case_dirs:
        for case_dir in case_dirs:
            if case_dir.is_dir():
                amount_case_dirs += 1
    return amount_case_dirs

indicator_patterns = [
    r"(?<=\W)art.?\s+",
    r"(?<=\W)artikel",
    r"(?<=\W)article",
    r"(?<=\W)artiekel",
    r"(?<=\W)W(?:lid|leden)\s+[0-9a-z]",
    r"[0-9]+[:.][0-9a-z]+"
]

# all_patterns = "(?:" + "|".join(indicator_patterns) + ")"

def get_indicator_spans(text):
    spans = []
    for pattern in indicator_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span = match.span()
            spans.append({
                "text": match.group(),
                "context": text[max(span[0] - 32, 0):min(span[1] + 32, len(text))],
                "span": match.span(),
            })
    return spans

def get_lido_spans(text, lido_links):
    # "type": "artikel",
    # "number": "353",
    # "bwb_id": "BWBR0001827",
    # "bwb_label_id": 3181564,
    # "title": "Wetboek van Burgerlijke Rechtsvordering (geldt in geval van digitaal procederen), Artikel 353",
    # "opschrift": "artikel 353 lid 1 Rv",
    # "source": "lido-ref"

    spans = []
    for lido_link in lido_links:
        # Use re.escape in case the string has special regex chars
        pattern = re.compile(re.escape(lido_link["opschrift"]), re.IGNORECASE)
        for match in pattern.finditer(text):
            spans.append({
                "text": match.group(),
                "span": match.span(),
                "title": lido_link["title"]
            })
    
    return spans

def span_in(span_a, span_b):
    """
    Returns True if span_a is fully contained in span_b.
    Each span is [start, end].
    """
    return span_b[0] <= span_a[0] and span_a[1] <= span_b[1]

def analyze_2():
    amount_case_samples = get_amount_case_samples()
    
    logging.info(f"Starting analysis (method 2) on {amount_case_samples} samples...")
    logging.info("")

    logging.info(f" {"ECLI-ID":<30} | {"length":<8} | {"links":<4} | {"indicators":<4} || {"not contained":<3}")
    logging.info(f" -------------------------------+----------+-------+------------++--------------")
    
    with os.scandir(DIR_ANALYSIS_DATA) as case_dirs:
        for case_dir in case_dirs:
            if case_dir.is_dir():

                # read full-text and lido links
                case_ecli = os.path.basename(case_dir)
                with open(os.path.join(case_dir, FILENAME_CASE_TEXT)) as f:
                    case_text = f.read()
                with open(os.path.join(case_dir, FILENAME_CASE_LIDO_LINKS)) as f:
                    case_lido_links_json = f.read()
                    case_lido_links = json.loads(case_lido_links_json)
                
                # compute custom links
                indicator_link_spans = get_indicator_spans(case_text)

                # save custom links
                with open(os.path.join(case_dir, FILENAME_CASE_INDICATORS), "w") as f:
                    f.write(json.dumps(indicator_link_spans, indent=4))
                
                # 1. find indicators and their spans
                # indicator_spans = get_indicator_spans(case)
                
                # 2. find spans of links in lido links
                lido_link_spans = get_lido_spans(case_text, case_lido_links)

                # 3. determine which of indicator_spans are not contained within lido_link_spans
                not_in_lido = []
                for indicator_span in indicator_link_spans:
                    found = False
                    for lido_span in lido_link_spans:
                        if span_in(indicator_span["span"], lido_span["span"]):
                            found = True
                            break
                    if not found:
                        not_in_lido.append(indicator_span)

                logging.info(f" {case_ecli:<30} | {len(case_text):>8} | {len(case_lido_links):>5} | {len(indicator_link_spans):<9}  || {len(not_in_lido):<3}")

                with open(os.path.join(case_dir, FILENAME_CASE_ANALYSIS), "w") as f:
                    f.write(json.dumps(not_in_lido, indent=4))
    
    # with open(FILE_STATS, 'a') as f:
    #     if f.tell() == 0:
    #         f.write("date;TP;FP;FN\n")
    #     f.write(datetime.now().isoformat(timespec="minutes") + ";" + ";".join([str(x) for x in confusion_matrix.values()]) + "\n")
