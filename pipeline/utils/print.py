import sys


def printerr(*values: object):
    print(*values, file=sys.stderr)