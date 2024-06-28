import os
import sys
import json
import random
import re
import logging
from pathlib import Path
from urllib.parse import quote_plus
from collections import defaultdict
from lxml import etree  # type: ignore

import asyncio
from aiohttp import ClientSession

CACHE_DIR = Path.home() / ".cache" / "fakeua"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BASE_PAGE = "http://useragentstring.com/pages/useragentstring.php?name={browser}"
BROWSERS = {"chrome": 80.7, "edge": 5.6, "firefox": 6.1, "safari": 3.7, "opera": 2.4}
BROWSER_SHORTCUTS = {
    "internet explorer": "edge",
    "ie": "edge",
    "google": "chrome",
    "googlechrome": "chrome",
    "ff": "firefox",
}
BROWSER_NUM = 50

OP = ["FETCHING", "PARSING"]
CACHE_FILE = ""
all_versions = defaultdict(list)


def get_cache(dir):
    logger.debug(f"Got cache folder: {dir}")
    for _, _, files in os.walk(dir):
        for f in files:
            match = re.search(r"^fake_useragent_", f)
            if match:
                logger.debug(f"{f} is found.")
                return os.path.join(dir, f)

    logger.debug("No cache is found.")
    return ""


async def fetch(url, session):
    attempt = 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36"}

    while True:
        try:
            async with session.get(url, headers=headers, timeout=9, ssl=False) as resp:
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
    attempt += 1
    logger.debug(f"{op} {url} {attempt} times")
    if attempt == 3:
        print(f"Maximum {op} reached: {error}")
        sys.exit(1)
    return attempt


async def parse(browser, session):
    url = BASE_PAGE.format(browser=quote_plus(browser))
    html_str = await fetch(url, session)
    lxml_element = etree.HTML(html_str)

    attempt = 0
    while True:
        try:
            versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[:BROWSER_NUM]
        except Exception as e:
            attempt = call_on_error(e, url, attempt, OP[1])
            continue
        else:
            if not versions:
                logger.debug(str(ValueError("Nothing parsed out")))
                return None

            logger.debug(f"{browser} has been parsed successfully")
            return versions


async def write_to_dict(browser, session):
    global all_versions
    versions = await parse(browser, session)
    if versions is None:
        versions = read("../backup/fake_useragent.json")[browser]

    all_versions[browser].extend(versions)
    logger.debug(f"{browser} versions has been written to all_versions\n")


def write(path, data):
    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)

    logger.debug(f"Cache has been stored in {path}\n")

    global CACHE_FILE
    CACHE_FILE = path


def read(path):
    with open(path, encoding="utf-8", mode="rt") as f:
        cache_data = f.read()

    logger.debug(f"Read {path} successfully")
    return json.loads(cache_data)


def rm_cache():
    cache = get_cache(CACHE_DIR)
    if not cache:
        print("No cache found to be deleted.")
        return

    os.remove(cache)

    file_name = cache.split("/")[-1]
    print(f"{file_name} has been removed successfully.")

    global CACHE_FILE
    CACHE_FILE = ""


def get_browser(browser):
    if not browser:
        logger.debug("A browser will be randomly given")
        browser = random.choices(
            list(BROWSERS.keys()),
            weights=list(BROWSERS.values()),
            k=1,
        )[0]

    else:
        logger.debug(f"{browser} will be formatted")
        browser = browser.strip().lower()
        browser = BROWSER_SHORTCUTS.get(browser, browser)
        if browser not in list(BROWSERS.keys()):
            print(f"Browser name '{browser}' is not supported.")
            print("Supported browsers: chrome, edge, firefox, safari, opera")
            print("\nPlease try again with one of the supported browser names.")
            sys.exit()

    return browser


def get_input():
    args = parse_args()
    try:
        if args.version:
            print("fake_user_agent " + __version__)
            sys.exit()

        if args.remove:
            rm_cache()
            sys.exit()

        if args.debug:
            logger.setLevel(logging.DEBUG)

        browser = args.browser

        if args.nocache:
            print(asyncio.run(main(browser=browser, use_cache=False)))
        else:
            print(asyncio.run(main(browser=browser, use_cache=True)))

    except KeyboardInterrupt:
        print("\nStopped by user.")


async def main(browser=None, use_cache=True):
    browser = get_browser(browser)
    logger.debug(f'Got "{browser}".')

    if not use_cache:
        async with ClientSession() as session:
            versions = await parse(browser, session)
            if versions is None:
                logger.debug("Reading from backup data...")
                backup_data = read("../backup/fake_useragent.json")
                return random.choice(backup_data[browser])
            return random.choice(versions)

    else:
        cache = get_cache(CACHE_DIR)
        global CACHE_FILE
        CACHE_FILE = cache

        if CACHE_FILE:
            data = read(CACHE_FILE)
            return random.choice(data[browser])

        else:
            async with ClientSession() as session:
                tasks = []
                for b in BROWSERS.keys():
                    tasks.append(write_to_dict(b, session))
                await asyncio.gather(*tasks)

                write(CACHE, all_versions)
                result = str(random.choice(all_versions[browser]))
                return result


def user_agent(browser=None, use_cache=True):
    return asyncio.run(main(browser, use_cache))


if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fake_user_agent.log import logger
    from fake_user_agent.args import parse_args
    from fake_user_agent.__init__ import __version__

    CACHE = str(CACHE_DIR / "fake_useragent_{version}.json".format(version=__version__))
    get_input()

else:
    from .log import logger
    from .args import parse_args
    from .__init__ import __version__

    CACHE = str(CACHE_DIR / "fake_useragent_{version}.json".format(version=__version__))
