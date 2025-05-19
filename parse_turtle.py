from caselaw.db import get_conn, init_db
from caselaw.process_cases import process_ttl_cases
from caselaw.process_laws import process_ttl_laws
import sys

if __name__=="__main__":
    # process_ttl_cases(None, "data/dynamic/lido-export.ttl.gz")
    
    with get_conn("caselaw-dev.db") as conn:
        init_db(conn)
        
        # path = "./data/dynamic/lido-export.ttl.gz"
        
        # process_ttl_laws(conn, "./data/dynamic/lido-law-sort.nt") # 2m13s
        process_ttl_cases(conn, "./data/dynamic/lido-cases-sort.nt")

        # process_all_triples(conn, path)

    # process_ttl_gz(conn, "data/dynamic/lido-export.ttl.gz")

    # Total number of sentences in turtle file is about: 19752995 (
    #   19752995 in python,
    #   19752982 in python without rstrip () (211.73s)
    #   19752969 with zcat and grep " \.$"")

    # Total number of 'law items', given the list regelingonderdelen
    # ...

    # Benchmarks                              n           t (s)
    # ---------------------------    ----------   -------------
    # w/o print, w/o strip (all)     19_752_982             211
    # before with print i                10_000              15.8 (5.5s system)
    # before without print               10_000               4.7
    # buffered reader print i            10_000               0.9
    # buffered reader w/o print i        10_000               0.3
    # buffered reader print i           100_000              11.3
    # buffered reader w/o print i       100_000               7.1 then 4.9
    
    # parse for law items               100_000              56
    # parse for law items (all)         888_635            1732.30 (28m)

    # parse w/ graph + insert             4_000              20      200/s
    #                                   184_000             560.83   320/s
    #
    # parsed count cases              3_575_771            2635.12

    # projection for scanning all articles    19752982 = 3.07h
