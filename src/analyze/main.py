from collections import Counter
import logging
import os
import json
from src.search import extract_links
from src.types import Link
from datetime import datetime

DIR_ANALYSIS_DATA = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
FILE_STATS = os.path.join(DIR_ANALYSIS_DATA, "stats.csv")
FILENAME_CASE_TEXT = "full_text.txt"
FILENAME_CASE_LIDO_LINKS = "links_lido.json"
FILENAME_CASE_CUSTOM_LINKS = "links_custom.json"
FILENAME_CASE_ANALYSIS = "analysis.json"

def get_amount_case_samples():
    amount_case_dirs = 0
    with os.scandir(DIR_ANALYSIS_DATA) as case_dirs:
        for case_dir in case_dirs:
            if case_dir.is_dir():
                amount_case_dirs += 1
    return amount_case_dirs

def compare_links(links_true, links_test):
    # true_set = Counter([tuple(link.items()) for link in links_true])
    # test_set = Counter([tuple(link.items()) for link in links_test])

    true_set = Counter(links_true)
    test_set = Counter(links_test)

    result_sets = {
        # true positives: items in the test set that are also in the true set
        "TP": true_set & test_set,
        # false positives: items in test that are not in true (or, they are correct and improve recall. high FP could indicate good potential improvement)
        "FP": test_set - true_set,
        # false negatives: items in true that are not in test, and should have been caught
        "FN": true_set - test_set
    }

    results = {}
    
    for metric, values in result_sets.items():
        results[metric] = [dict(link) | {"n": n} for link, n in values.items()] # type: ignore
    
    # return {metric: len(values) for metric, values in results.items()}
    return results

def normalize_lido_link(lido_link):
    # {
    #     "type": "artikel",
    #     "number": "17",
    #     "bwb_id": "BWBR0002170",
    #     "bwb_label_id": 2584134,
    #     "title": "Beroepswet, Artikel 17",
    #     "opschrift": "artikel 17 van de Beroepswet",
    #     "source": "lido-ref"
    # },
    if lido_link["type"] != "artikel":
        return None
    return tuple({
        "type": lido_link["type"],
        "number": lido_link["number"],
        "bwb_id": lido_link["bwb_id"],
        "bwb_label_id": lido_link["bwb_label_id"],
    }.items())

def normalize_custom_link(custom_link: Link):
    # {
    #     "type": "artikel",
    #     "number": "17",
    #     "bwb_id": "BWBR0002170",
    #     "bwb_label_id": 2584134,
    #     "title": "Beroepswet, Artikel 17",
    #     "opschrift": "artikel 17 van de Beroepswet",
    #     "source": "lido-ref"
    # },
    if not "fragment" in custom_link or not "artikel" in custom_link["fragment"]:
        return None
    if not "bwb_label_id" in custom_link["resource"]:
        return None
    return tuple({
        "type": "artikel",
        "number": custom_link["fragment"]["artikel"],
        "bwb_id": custom_link["resource"]["bwb_id"],
        "bwb_label_id": custom_link["resource"]["bwb_label_id"],
    }.items())

def analyze():
    amount_case_samples = get_amount_case_samples()
    
    logging.info(f"Starting analysis on {amount_case_samples} samples...")
    logging.info("")
    
    confusion_matrix = {
        'TP': 0, # links that custom found that are also in lido
        'FP': 0, # links that custom found that are not in lido
        # 'TN': None, # links that custom did not find, that are also not in lido
        #     # (valueless, not needed for recall, only for specificity, accuracy and type 1 errors)
        'FN': 0  # links that custom did not find, but lido did find
    }

    logging.info(f" {"ECLI-ID":<30} | {"length":<8} | {"links":<4}  || {"TP":<3} | {"FP":<3} | {"FN":<3}")
    logging.info(f" -------------------------------+----------+--------++-----+-----+----")
    
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

                # logging.info(f"Case {case_ecli} has {len(case_text)} chars and {len(case_lido_links)} links")
                
                # compute custom links
                case_custom_links = extract_links(case_text)

                # save custom links
                with open(os.path.join(case_dir, FILENAME_CASE_CUSTOM_LINKS), "w") as f:
                    f.write(json.dumps(case_custom_links, indent=4))
                
                case_custom_links_dedup = []
                seen_literals = set()
                for link in case_custom_links:
                    if link["context"]["literal"] is not None and link["context"]["literal"].lower() not in seen_literals:
                        case_custom_links_dedup.append(link)
                        seen_literals.add(link["context"]["literal"].lower())
                
                # normalize and make case links hashable (tuple)
                case_lido_links_normalized = list([
                    link for link in [normalize_lido_link(link) for link in case_lido_links] if link is not None
                ])
                case_custom_links_normalized = list([
                    link for link in [normalize_custom_link(link) for link in case_custom_links_dedup] if link is not None
                ])
                
                # save titles to lookup dictionary
                title_lookup = {}
                for link in case_lido_links:
                    title_lookup[str(link['bwb_label_id'])] = link['title']
                for link in case_custom_links:
                    title_lookup[str(link['resource']['bwb_label_id'])] = link['resource']['title']

                # compare lido and custom links
                diff = compare_links(case_lido_links_normalized, case_custom_links_normalized)

                # reapply titles to diff results
                diff = {metric: [obj | {"title": title_lookup[str(obj['bwb_label_id'])]} for obj in value] for metric, value in diff.items()}

                diff_metrics = {metric: sum(v["n"] for v in values) for metric, values in diff.items()}

                logging.info(f" {case_ecli:<30} | {len(case_text):>8} | {len(case_lido_links):>5}  || {diff_metrics['TP']:>3} | {diff_metrics['FP']:>3} | {diff_metrics['FN']:>3}")

                with open(os.path.join(case_dir, FILENAME_CASE_ANALYSIS), "w") as f:
                    f.write(json.dumps(diff, indent=4))
                
                for metric, fields in diff_metrics.items():
                    confusion_matrix[metric] += fields
    
    with open(FILE_STATS, 'a') as f:
        if f.tell() == 0:
            f.write("date;TP;FP;FN\n")
        f.write(datetime.now().isoformat(timespec="minutes") + ";" + ";".join([str(x) for x in confusion_matrix.values()]) + "\n")
