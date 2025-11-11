from linkextractor.analyze.method_2 import analyze_2
from linkextractor.analyze.prepare import prepare, prepare_specific
from linkextractor.db import set_db_url
from linkextractor.search import extract_links
from linkextractor.utils import get_cases_by_bwb_and_label_id
from linkextractor.analyze.method_1 import analyze
from linkextractor.test_queries import test_queries
import sys
import logging

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
        description="LinkExtractor CommandLine Interface",
        parents=[parent_parser]
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval = subparsers.add_parser(
        "eval",
        help="evaluate string",
        parents=[parent_parser]
    )
    eval.add_argument("-e", "--exact", help="match exact", action=argparse.BooleanOptionalAction)
    eval.add_argument("-n", "--no-trie", help="do not use trie for finding aliases", action=argparse.BooleanOptionalAction)
    eval.add_argument("text", nargs="?", help="text to parse from", type=str)

    parser_test = subparsers.add_parser(
        "test",
        help="test predefined queries",
        parents=[parent_parser]
    )

    parser_analyze = subparsers.add_parser(
        "analyze",
        help="run pipeline for analysis of texts from db",
        parents=[parent_parser]
    )
    
    parser_analyze.add_argument("-p", "--prepare", help="prepare", action="store_true")
    parser_analyze.add_argument("-c", "--cherry-pick", help="cherry pick", type=str)
    parser_analyze.add_argument("-n", "--samples", help="amount of samples to prepare (use with --prepare)", type=int)
    parser_analyze.add_argument("-s", "--seed", help="seed for getting random sample from db", type=int)
    parser_analyze.add_argument("-2", "--method-2", help="use second method for analysis", action="store_true")

    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s" 
    )

    if args.database is not None:
        set_db_url(args.database)

    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(0)

    if args.command == "eval":
        if args.text is None:
            args.text = sys.stdin.read()
        if args.text is None:
            parser.error("argument 'text' is required, either as a literal or redirected via stdin")

        use_trie = True
        if args.no_trie is not None and args.no_trie:
            use_trie = False
        
        results = []
        
        start = time()
        if args.exact:
            results = extract_links(args.text, exact=True, use_trie=use_trie)
        else:
            results = extract_links(args.text, exact=False, use_trie=use_trie)

        logging.debug("found %s results in %ss", len(results), round(time()-start, 3))
        for result in results:
            print(result)
            # logging.info(result)

    elif args.command == "test":
        test_queries()

    elif args.command == "analyze":
        if args.samples is not None and args.prepare is None:
            parser.error("argument -n/--samples requires -p/--prepare")
        if args.seed is not None and args.prepare is None:
            parser.error("argument -s/--seed requires -p/--prepare")
        if args.cherry_pick is not None and args.prepare is None:
            parser.error("argument -c/--cherry-pick requires -p/--prepare")
            
        if args.prepare:
            if args.cherry_pick:
                prepare_specific(args.cherry_pick)
            else:
                prepare(args.samples, args.seed)
        if args.method_2:
            analyze_2()
        else:
            analyze()

if __name__ == "__main__":
    main()