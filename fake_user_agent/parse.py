import argparse

def parse_args():
    """Get the arguments from command line"""
    parser = argparse.ArgumentParser(
        description="fakeua is a tool to generate a fake useragent randomly."
    )
    parser.add_argument(
        "browser",
        nargs="?",
        default="",
        help="Supported values: chrome, edge, firefox, safari, opera. Case insensitive.",
    )

    args = parser.parse_args()
    return args


def get_browser_input():
    return parse_args().browser
