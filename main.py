from src.db import set_db_url
from src.search import query_exact, query_in_text
from src.utils import get_cases_by_bwb_and_label_id
import sys

import argparse

# start set wrkdir
import os
import pathlib
from typing import List, Union
from statistics import median
from time import time

script_dir = pathlib.Path(__file__).parent.resolve()
os.chdir(script_dir)
# end set wrkdir

def main():
    # Global parser with args for every parser
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    parent_parser.add_argument(
        "-d", "--database",
        action="store",
        help="Specify database. Default",
        default=None
    )

    parser = argparse.ArgumentParser(
        description="LinkExtractor-Lite CommandLine Interface",
        parents=[parent_parser]
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval = subparsers.add_parser(
        "eval",
        help="evaluate string",
        parents=[parent_parser]
    )
    eval.add_argument("-e", "--exact", help="match exact", action=argparse.BooleanOptionalAction)
    eval.add_argument("string", help="string to parse from", type=str)

    test = subparsers.add_parser(
        "test",
        help="test predefined queries",
        parents=[parent_parser]
    )

    analyze = subparsers.add_parser(
        "analyze",
        help="run pipeline for analysis of texts from db",
        parents=[parent_parser]
    )

    args = parser.parse_args()

    if args.database is not None:
        set_db_url(args.database)

    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(0)

    if args.command == "eval":
        results = []

        if args.exact:
            results = query_exact(args.string, args.verbose)
        else:
            results = query_in_text(args.string, args.verbose)

        for result in results:
            print(result)

    elif args.command == "test":
        test_queries()

    elif args.command == "analyze":
        print("Brrrr")


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

    print("DB_BACKEND:", DB_BACKEND)

    for i, query in enumerate(queries):
        print(f"{i}) Query: \"{query}\"")

        times = []
        iterations = 1
        for _ in range(iterations):
            time_s = time()
            # results = query_in_text(query)
            results = query_exact(query)
            times.append(time() - time_s)
        print("  Search performance:")
        print(f"  - Iterations:  {iterations}")
        print(f"  - Min time:    {round(min(times), 5)}")
        print(f"  - Mean time:   {round(sum(times) / len(times), 5)}")
        print(f"  - Median time: {round(median(times), 5)}")
        print(f"  - Max time:    {round(max(times), 5)}")
        print()

        if len(results) > 0:
            print("  Results:")
            for i, element in enumerate(results):
                print(f"  - Element {i}: {element}")
                if GET_CASES:
                    cases = get_cases_by_bwb_and_label_id(element['bwb_id'], element['bwb_label_id'])
                    if len(cases) > 0:
                        print(f"      - Cases in element {i}: {len(cases)}")
                        for k, case in enumerate(cases):
                            print(f"        - {k}: {case}")

            print()
        else:
            print("  No results.")
        print()

        if FIRST_ONLY:
            break



if __name__ == "__main__":
    main()
    quit()
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
