import random
import os
import shutil
import json
import logging

from src.db import DB_BACKEND, get_conn
from .main import DIR_ANALYSIS_DATA, FILENAME_CASE_TEXT, FILENAME_CASE_LIDO_LINKS

def generate_id_list(n, max, seed):
    """
    Generate a list of n unique random integers between 0 and max (inclusive).
    
    Args:
        n (int): Number of unique integers to generate.
        max (int): Maximum value allowed.
        seed (int, optional): Seed for random number generator. Default is 42.
    
    Returns:
        list[int]: List of n unique random integers.
    
    Raises:
        ValueError: If n > (max + 1), because we can’t pick more unique numbers than available.
    """
    if n > max + 1:
        raise ValueError(f"Cannot pick {n} unique numbers from range 0..{max}")
    
    random.seed(seed)
    return random.sample(range(max + 1), n)

def get_case_by_idx(cursor, idx):
    cursor.execute("select ecli, full_text from ecli_texts order by ecli limit 1 offset %s;", (idx,))
    return cursor.fetchone()
    
def get_lido_links_by_ecli(cursor, ecli):
    lido_links = []
    
    cursor.execute("""
        SELECT l.type, l.number, l.bwb_id, l.bwb_label_id, l.title, cl.opschrift, cl.source
        FROM law_element l
        JOIN case_law cl ON (cl.law_id = l.id)
        JOIN legal_case c ON (cl.case_id = c.id)
        WHERE 
            c.ecli_id = %s
            AND cl.source = 'lido-ref'
        GROUP BY l.bwb_label_id, l.type, l.number, l.bwb_id, l.bwb_label_id, l.title, cl.opschrift, cl.source
    """, (ecli,))
    
    for lido_link in cursor:
        row_dict = dict(zip([desc[0] for desc in cursor.description], lido_link))
        lido_links.append(row_dict)
    
    return lido_links

# def get_rows_by_id_list(id_list):
#     return results

def prepare(sample_size = None, seed = None):
    # if sample_size is None: sample_size = 1000
    if sample_size is None: sample_size = 10
    if seed is None: seed = 42
    
    logging.debug(f"Preparing analysis directory with sample of size {sample_size}...")
    
    # 0. clear data dir
    # 1. generate seeded-random list of indexes for retrieving from the database
    # 2. fetch full-texts from database and place in data folder
    # 3. fetch links of corresponding texts from database as ground-truth for (atleast) true-positives
    
    # 0. clear data dir
    for entry in os.listdir(DIR_ANALYSIS_DATA):
        full_path = os.path.join(DIR_ANALYSIS_DATA, entry)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path) 
    
    # 1. generate seeded-random list of indexes for retrieving from the database
    # items in ecli_text as of 2025-9-3: 98966
    id_list = generate_id_list(sample_size, 95000, seed)
    
    # 2. fetch full-texts from database and place in data folder
    assert DB_BACKEND == "postgres", "expects postgres backend"
    
    conn = get_conn()
    cursor = conn.cursor()
    
    for idx in id_list:
        case = get_case_by_idx(cursor, idx)
        
        if case is None:
            continue
        
        (case_ecli, case_full_text,) = case
        
        path_case = os.path.join(DIR_ANALYSIS_DATA, str(case_ecli))
        path_case_text = os.path.join(path_case, FILENAME_CASE_TEXT)
        path_case_lido_links = os.path.join(path_case, FILENAME_CASE_LIDO_LINKS)
        os.makedirs(path_case)
        
        with open(path_case_text, 'w') as f:
            f.write(case_full_text)
        
        # 3. fetch links of corresponding texts from database as ground-truth for (atleast) true-positives
        lido_links = get_lido_links_by_ecli(cursor, case_ecli)
        
        lido_links_json = json.dumps(lido_links, indent=4)
        
        with open(path_case_lido_links, 'w') as f:
            f.write(lido_links_json)
        
    logging.debug("Preperation done")
