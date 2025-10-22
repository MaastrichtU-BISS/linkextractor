import logging
from statistics import median
from time import time

from linkextractor.db import DB_BACKEND
from linkextractor.search import extract_links
from linkextractor.utils import get_cases_by_bwb_and_label_id

def test_queries():

    queries = [
        "Art. 7:658 BW",
        "Artikel 7:658 BW",
        "Artikel 7:658 Burgerlijk Wetboek", # geen resultaat op linkeddata
        "Artikel 7:658 van het BW", # geeft resultaat
        "Artikel 7:658 van het BW boek 7", # geeft geen resultaat maar wel geldig
        "Artikel 658 van boek 7 van het Burgerlijk Wetboek",
        "Artikel 658 van het boek 7 van het Burgerlijk Wetboek",
        "Burgerlijk Wetboek Boek 7, Artikel 658",
        "Burgerlijk Wetboek, Artikel 658",
        "Artikel 658 van Boek 7 BW",
        "Art. 7:658 van het Burgerlijk Wetboek",
        "Ik heb dat gelezen in art. 7:658 BW of in BW, artikel 5.",
        "Burgerlijk Wetboek",

        # van xslx ->
        "Artikel 1:75 Wet op het financieel toezicht",
        "1:75 Wft",

        "Artikel 3 Wet ter voorkoming van witwassen en financieren van terrorisme (cliëntenonderzoek)",
        "Artikel 16 Wet ter voorkoming van witwassen en financieren van terrorisme (FIU-meldplicht)",
        "Artikel 61 Wet toezicht trustkantoren 2018 (publicatie bestuurlijke boete)",
        "Artikel 3:2 Algemene wet bestuursrecht (zorgvuldigheidsbeginsel)",
        "Artikel 3:2 Algemene wet bestuursrecht (zorgvuldigheidsbeginsel) + DNB OR AFM",
        "3:2 awb",

        "Artikel 4:8 Algemene wet bestuursrecht (hoor en wederhoor)", # <-- article is "4:8" ? but could also be interpreted as book 4 article 8
        "4:8 Awb",

        "Verordening (EG) nr. 1618/1999",

        "Artikel 7.4 WHW",
        "Artikel 7.12B WHW",
        "Artikel 7.28 WHW",
        "Artikel 7.30b WHW",
        "Artikel 7.57H WHW",
        "Artikel 7.61 WHW",
        "Artikel 9.19 WHW",
        "5:1 BW",
        "art. 1 Wet gelijke behandeling op grond van handicap of chronische ziekte",

        "art. 2:346 lid 1, aanhef en onder e BW",
        "Burgerlijk Wetboek Boek 7, Artikel 658",

        "Art. 5:1 lid 2 BW",
    ]

    FIRST_ONLY = True
    GET_CASES = True
    # FIRST_ONLY = False
    # GET_CASES = False

    logging.debug("DB_BACKEND:", DB_BACKEND)

    for i, query in enumerate(queries):
        logging.debug(f"{i}) Query: \"{query}\"")

        times = []
        iterations = 1
        for _ in range(iterations):
            time_s = time()
            # results = extract_links(query)
            results = extract_links(query, exact=True)
            times.append(time() - time_s)
        logging.info("  Search performance:")
        logging.info(f"  - Iterations:  {iterations}")
        logging.info(f"  - Min time:    {round(min(times), 5)}")
        logging.info(f"  - Mean time:   {round(sum(times) / len(times), 5)}")
        logging.info(f"  - Median time: {round(median(times), 5)}")
        logging.info(f"  - Max time:    {round(max(times), 5)}")
        logging.info("")

        if len(results) > 0:
            logging.info("  Results:")
            for i, element in enumerate(results):
                logging.info(f"  - Element {i}: {element}")
                if GET_CASES:
                    cases = get_cases_by_bwb_and_label_id(element['resource']['bwb_id'], element['resource']['bwb_label_id'])
                    if len(cases) > 0:
                        logging.info(f"      - Cases in element {i}: {len(cases)}")
                        for k, case in enumerate(cases):
                            logging.info(f"        - {k}: {case}")

            logging.info("")
        else:
            logging.info("  No results.")
        logging.info("")

        if FIRST_ONLY:
            break


# prepare()

# ## START GET PERMUTATIONS
# perms = query_perms("Art 5:1 BW", debug=False)
# for (i, perm, ) in enumerate(perms):
#     print(i, perm)
# exit()
# ## END GET PERM.

# a = find_matching_aliases(f"Algemene wet bestuursrecht", wildcard=('r'))

"""
TODO improvements:
 - ensure that single matches are not part of words (such as "Burgerlijk Wetboek" matching "LI" -> Liftenbesluit, etc.)
   [-] ensure that matches in find_aliases_in_text are not part or words
   - ensure that when finding relevant wildcards in find_matching_aliases, it is either that or has a space
 [-] for found matched aliases, search its id and return the longest alias given that id
 - simpler implementation for only search
 [-] nice output, with article if included (json)

 - performance, keep dataabse connection open

 Edge cases
 - awb:
    -> on linkeddata, only Algemene Wet Bestuursrecht
    -> In here, there seem many aliases of AWB with longer full names
 - burgelijk wetboek
    -> returns much to many offsets
 - bw, artikel 5
    -> should return all of BW with suffixes (maybe it does but restricted by results)
"""
