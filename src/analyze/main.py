import logging
import os
import json
from src.search import extract_in_text
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
    true_set = set([tuple(link.items()) for link in links_true])
    test_set = set([tuple(link.items()) for link in links_test])

    # true_set = set(links_true)
    # test_set = set(links_test)

    result_sets = {
        # true positives: items in the test set that are also in the true set
        "TP": true_set & test_set,
        # false positives: items in test that are not in true (or, they are correct and improve recall. high FP could indicate good potential improvement)
        "FP": test_set - true_set,
        # false negatives: items in true that are not in test, and should have been caught
        "FN": true_set - test_set
    }

    # TP = true_set ^ test_set 
    # FP = test_set - true_set 
    # FN = true_set - test_set 

    # TP = [dict(x) for x in TP]
    # FP = [dict(x) for x in FP]
    # FN = [dict(x) for x in FN]

    results = {}
    
    for metric, values in result_sets.items():
        results[metric] = [dict(x) for x in values] # type: ignore
    
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
    return {
        "type": lido_link["type"],
        "number": lido_link["number"],
        "bwb_id": lido_link["bwb_id"],
        "bwb_label_id": lido_link["bwb_label_id"],
    }

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
    return {
        "type": "artikel",
        "number": custom_link["fragment"]["artikel"],
        "bwb_id": custom_link["resource"]["bwb_id"],
        "bwb_label_id": custom_link["resource"]["bwb_label_id"],
    }

def analyze():
    amount_case_samples = get_amount_case_samples()
    
    logging.info(f"Starting analysis on {amount_case_samples} samples...")
    
    confusion_matrix = {
        'TP': 0, # links that custom found that are also in lido
        'FP': 0, # links that custom found that are not in lido
        # 'TN': None, # links that custom did not find, that are also not in lido
        #     # (valueless, not needed for recall, only for specificity, accuracy and type 1 errors)
        'FN': 0  # links that custom did not find, but lido did find
    }
    
    with os.scandir(DIR_ANALYSIS_DATA) as case_dirs:
        for case_dir in case_dirs:
            if case_dir.is_dir():

                title_lookup = {}

                case_ecli = os.path.basename(case_dir)
                with open(os.path.join(case_dir, FILENAME_CASE_TEXT)) as f:
                    case_text = f.read()
                with open(os.path.join(case_dir, FILENAME_CASE_LIDO_LINKS)) as f:
                    case_lido_links_json = f.read()
                    case_lido_links = json.loads(case_lido_links_json)
                
                case_lido_links = list(filter(lambda link: link is not None, map(normalize_lido_link, case_lido_links)))

                logging.info(f"Case {case_ecli} has {len(case_text)} chars and {len(case_lido_links)} links")
                
                # compute custom links
                case_custom_links = extract_in_text(case_text)
                with open(os.path.join(case_dir, FILENAME_CASE_CUSTOM_LINKS), "w") as f:
                    f.write(json.dumps(case_custom_links, indent=4))

                case_custom_links = list(filter(lambda link: link is not None, map(normalize_custom_link, case_custom_links)))
                
                # compare lido and custom links
                diff = compare_links(case_lido_links, case_custom_links)

                if False:
                    diff_metrics = {}
                    for metric, values in diff.items():
                        diff_metrics[metric] = len(values)
                        logging.info(f"{metric} ({len(values)})")
                        if metric == "TP":
                            logging.info(f"✅ True Positives ({len(values)})")
                        elif metric == "FP":
                            logging.info(f"❔ False Positives (or wrong FP in true) ({len(values)})")
                        elif metric == "FN":
                            logging.info(f"❗ False Negatives (should be caught) ({len(values)})")
                        for item in values:
                            logging.info(f"-> {item['type']} {item['number']} ({item['bwb_id']}:{item['bwb_label_id']})")

                diff_metrics = {metric: len(values) for metric, values in diff.items()}
                logging.info(f"Difference: {diff_metrics}")

                with open(os.path.join(case_dir, FILENAME_CASE_ANALYSIS), "w") as f:
                    f.write(json.dumps(diff, indent=4))
                
                for metric, fields in diff_metrics.items():
                    confusion_matrix[metric] += fields
    
    with open(FILE_STATS, 'a') as f:
        if f.tell() == 0:
            f.write("date;TP;FP;FN\n")
        f.write(datetime.now().isoformat(timespec="minutes") + ";" + ";".join([str(x) for x in confusion_matrix.values()]) + "\n")