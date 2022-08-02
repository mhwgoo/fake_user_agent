import argparse


def parse_args():
    """Get the arguments from command line."""

    parser = argparse.ArgumentParser(
        description="fakeua is a tool to generate a fake useragent randomly."
    )

    parser.add_argument(
        "browser",
        nargs="?",
        default="",
        help="supported values: chrome, edge, firefox, safari, opera. Case insensitive",
    )

    parser.add_argument(
        "-n",
        "--nocache",
        action="store_true",
        help="set to get a useragent without local caching",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="set to get a useragent in debug mode",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="print the current version of the program",
    )

    parser.add_argument(
        "-r",
        "--remove",
        action="store_true",
        help="remove cache from tempfile folder",
    )

    args = parser.parse_args()
    return args
