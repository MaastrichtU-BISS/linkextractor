import logging
import os
import json
from src.search import extract_in_text

DIR_ANALYSIS_DATA = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
FILE_STATS = os.path.join(DIR_ANALYSIS_DATA, "stats.csv")
FILENAME_CASE_TEXT = "full_text.txt"
FILENAME_CASE_LIDO_LINKS = "links_lido.json"

def get_amount_case_samples():
    amount_case_dirs = 0
    with os.scandir(DIR_ANALYSIS_DATA) as case_dirs:
        for case_dir in case_dirs:
            if case_dir.is_dir():
                amount_case_dirs += 1
    return amount_case_dirs

def compare_links(links_true, links_test):
    
    return {}

def analyze():
    amount_case_samples = get_amount_case_samples()
    
    logging.info(f"Starting analysis on {amount_case_samples} samples...")
    
    confusion_matrix = {
        'TP': 0, # links that custom found that are also in lido
        'FP': 0, # links that custom found that are not in lido
        'TN': None, # links that custom did not find, that are also not in lido
            # (valueless, not needed for recall, only for specificity, accuracy and type 1 errors)
        'FN': 0  # links that custom did not find, but lido did find
    }
    
    with os.scandir(DIR_ANALYSIS_DATA) as case_dirs:
        for case_dir in case_dirs:
            if case_dir.is_dir():
                case_ecli = os.path.basename(case_dir)
                with open(os.path.join(case_dir, FILENAME_CASE_TEXT)) as f:
                    case_text = f.read()
                with open(os.path.join(case_dir, FILENAME_CASE_LIDO_LINKS)) as f:
                    case_lido_links_json = f.read()
                    case_lido_links = json.loads(case_lido_links_json)
                
                logging.info(f"Case {case_ecli} has {len(case_text)} chars and {len(case_lido_links)} links")
                
                # compute custom links
                case_custom_links = extract_in_text(case_text)
                
                # compare lido and custom links
                diff = compare_links(case_lido_links, case_custom_links)
    
    with open(FILE_STATS, 'a') as f:
        f.write(",".join([str(x) for x in confusion_matrix.values()]) + "\n")