import os
import json

DIR_ANALYSIS_DATA = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
FILE_STATS = "stats.csv"
FILENAME_CASE_TEXT = "full_text.txt"
FILENAME_CASE_LIDO_LINKS = "links_lido.json"

def get_amount_case_samples():
    amount_case_dirs = 0
    with os.scandir(DIR_ANALYSIS_DATA) as case_dirs:
        for case_dir in case_dirs:
            if case_dir.is_dir():
                amount_case_dirs += 1
    return amount_case_dirs

def analyze():
    amount_case_samples = get_amount_case_samples()
        
    print(f"Starting analysis on {amount_case_samples} samples...")
    
    confusion_matrix = {
        'TP': 0, # links that custom found that are also in lido
        'FP': 0, # links that custom found that are not in lido
        'TN': 0, # links that custom did not find, that are also not in lido (valueless, not needed for recall, only for specificity, accuracy and type 1 errors)
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
                
                print(f"Case {case_ecli} has {len(case_text)} chars and {len(case_lido_links)} links")
                
                # compute custom links
                
                # compare lido and custom links 