"""
Main script to randomly generate a fake useragent.

WARNING:
This module name has been changed from main.py since version 2.1.0. Now it's user_agent.py.
This change is made in order to display better debugging message when the module is imported in third-party module.
If you are using `from fake_user_agent.main import user_agent`, You need to change it to `from fake_user_agent import user_agent`.
"""

import os
import json
import random
import sys
import time
import logging
from urllib.parse import quote_plus
from collections import defaultdict
from lxml import etree
from functools import wraps

# for asynchronous programming
import asyncio
from aiohttp import ClientSession

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from fake_user_agent import settings
# from fake_user_agent.log import logger
# from fake_user_agent.args import parse_args

from . import settings
from .log import logger
from .args import parse_args


all_versions = defaultdict(list)  # a dict created with its values being list

OP = ["FETCHING", "PARSING"]

CACHE_FILE = ""


async def fetch(url, session):
    """Fetch html text file using aiohttp session."""

    attempt = 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36"}

    while True:
        try:
            async with session.get(url, headers=headers, timeout=settings.HTTP_TIMEOUT, ssl=False) as resp:
                result = await resp.text()
        except asyncio.TimeoutError as e:
            attempt = call_on_error(e, url, attempt, OP[0])
            continue
        except Exception as e:
            attempt = call_on_error(e, url, attempt, OP[0])
            continue
        else:
            logger.debug(f"{url} has been fetched successfully")
            return result


def call_on_error(error, url, attempt, op):
    """Retry mechanism when an error occurs."""

    attempt += 1
    logger.debug("%s %s %d times", op, url, attempt)
    if attempt == 3:
        logger.debug("Maximum %s retries reached: %s", op, str(error))
        sys.exit()
    return attempt


async def parse(browser, session):
    """Parse out a browser's versions."""

    url = settings.BROWSER_BASE_PAGE.format(browser=quote_plus(browser))
    html_str = await fetch(url, session)
    lxml_element = etree.HTML(html_str)

    attempt = 0
    while True:
        try:
            # data type of the list:  <class 'lxml.etree._ElementUnicodeResult'>
            versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[:settings.BROWSERS_COUNT_LIMIT]
        except Exception as e:
            attempt = call_on_error(e, url, attempt, OP[1])
            continue
        else:
            if not versions:
                # attempt = call_on_error(ValueError("Nothing parsed out"), url, attempt, OP[1])
                # continue
                logger.debug(str(ValueError("Nothing parsed out")))
                return None

            logger.debug(f"{browser} has been parsed successfully")
            return versions


async def write_to_dict(browser, session):
    """Write versions to the `all_versions` dict {browser:versions}."""

    global all_versions
    versions = await parse(browser, session)
    if versions is None:
        versions = read("../backup/fake_useragent.json")[browser]

    all_versions[browser].extend(versions)  # add each element of versions list to the end of the list to be extended
    logger.debug(f"{browser} versions has been written to all_versions")


def write(path, data):
    """Write a json cache if there isn't one, or update it if any."""

    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)

    logger.debug(f"Cache has been stored in {path}\n")

    global CACHE_FILE
    CACHE_FILE = path


def read(path):
    """Read from a json file into a python object. Here the object is a dict."""

    with open(path, encoding="utf-8", mode="rt") as f:
        cache_data = f.read()

    logger.debug(f"Read {path} successfully\n")
    return json.loads(cache_data)


def rm_cache():
    """Remove cache if any."""

    cache = settings.get_cache(settings.CACHE_DIR)
    if not cache:
        print("No cache found to be deleted.")
        return

    os.remove(cache)

    file_name = cache.split("/")[-1]
    print(f"{file_name} has been removed successfully.")

    global CACHE_FILE
    CACHE_FILE = ""


def get_browser(browser):
    """If browser name is not given, randomly choose one browser based on weights set in settings.BROWSERS."""

    if not browser:
        logger.debug("A browser will be randowly given")
        browser = random.choices(
            list(settings.BROWSERS.keys()),
            weights=list(settings.BROWSERS.values()),
            k=1,
        )[0]

    else:
        logger.debug(f"{browser} will be formatted")
        browser = browser.strip().lower()
        browser = settings.SHORTCUTS.get(browser, browser)
        if browser not in list(settings.BROWSERS.keys()):  # transform an iterator to a list
            print(f"Browser name '{browser}' is not supported.")
            print("Supported browsers: chrome, edge, firefox, safari, opera")
            print("\nPlease try again with one of the supported browser names.")
            sys.exit()

    return browser


# ----------main----------

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_at = time.time()
        f = func(*args, **kwargs)
        time_taken = round((time.time() - start_at), 4)
        print("\nTime taken: {} seconds".format(time_taken))
        return f

    return wrapper


async def main(browser=None, use_cache=True):
    browser = get_browser(browser)
    logger.debug(f"Got {browser}")

    if not use_cache:
        async with ClientSession() as session:
            versions = await parse(browser, session)
            if versions is None:
                logger.debug(f"Reading from backup data...")
                backup_data = read("../backup/fake_useragent.json")
                return random.choice(backup_data[browser])
            return random.choice(versions)

    else:
        cache = settings.get_cache(settings.CACHE_DIR)
        global CACHE_FILE
        CACHE_FILE = cache

        if CACHE_FILE:
            data = read(CACHE_FILE)
            return random.choice(data[browser])

        else:
            async with ClientSession() as session:
                tasks = []
                for b in settings.BROWSERS.keys():
                    # Each iteration of a for loop, b gets assigned again.
                    # If b is named `browser` then `browser` value in the local space of the function will be set `settings.BROWSERS.keys()[-1]`
                    tasks.append(write_to_dict(b, session))
                await asyncio.gather(*tasks)

                write(settings.DB, all_versions)
                result = str(random.choice(all_versions[browser]))
                return result


@timer
def get_input():
    """Entry point for running fakeua binary on terminal."""

    args = parse_args()

    try:
        if args.version:
            print("fake_user_agent " + settings.VERSION)
            sys.exit()

        if args.remove:
            rm_cache()
            sys.exit()

        if args.debug:
            logging.getLogger(__package__).setLevel(logging.DEBUG)

        browser = args.browser

        if args.nocache:
            print(asyncio.run(main(browser=browser, use_cache=False)))
        else:
            print(asyncio.run(main(browser=browser, use_cache=True)))

    except KeyboardInterrupt:
        print("\nStopped by user.")


def user_agent(browser=None, use_cache=True):
    """Entry point for getting a user agent by importing this function in a python script."""

    return asyncio.run(main(browser, use_cache))


if __name__ == "__main__":
    get_input()
