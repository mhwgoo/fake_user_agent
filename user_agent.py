import os
import sys
import json
import random
import re
from pathlib import Path
from urllib.parse import quote_plus
from collections import defaultdict
from lxml import etree  # type: ignore

import asyncio
from aiohttp import ClientSession

#FIXME how to make logging exposable to caller
import logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s.%(filename)s[%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__package__)

#FIXME when updated to a new version, cache file should also be updated.

VERSION = "2.3.0"
CACHE_DIR = Path.home() / ".cache" / "fakeua"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE = str(CACHE_DIR / "fake_useragent_{version}.json".format(version=VERSION))

BASE_PAGE = "http://useragentstring.com/pages/useragentstring.php?name={browser}"

BROWSERS = {"chrome": 80, "edge": 86, "firefox": 93, "safari": 97, "opera": 100}
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36"
    }

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
            versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[
                :BROWSER_NUM
            ]
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


async def main(browser=None, use_cache=True):
    if browser is None:
        logger.debug("A browser will be randomly given.")
        browser = random.choices(list(BROWSERS.keys()), weights=list(BROWSERS.values()), k=1)[0]
        logger.debug(f'Got "{browser}".')
    else:
        logger.debug(f'You gave "{browser}".')
        browser = browser.strip().lower()
        if browser not in list(BROWSERS.keys()):
            logger.error(f'"{browser}" not supported, browser should be one of {list(BROWSERS.keys())}.')
            return None

    #TODO
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


async def aio_user_agent(browser=None, use_cache=True):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        return await loop.create_task(main(browser, use_cache))
    else:
        return asyncio.run(main(browser, use_cache))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Randomly generate a valid useragent for faking a browser.")
    parser.add_argument("browser", nargs="?", default="", help="supported values: chrome, edge, firefox, safari, opera. (case insensitive)")
    parser.add_argument("-d", "--debug", action="store_true", help="get a useragent in debug mode")
    parser.add_argument("-n", "--nocache", action="store_true", help="get a useragent without using local cache")
    parser.add_argument("-r", "--remove", action="store_true", help="remove cache from $HOME/.cache/fakeua")
    parser.add_argument("-v", "--version", action="store_true", help="print the current version of the program")
    args = parser.parse_args()
    try:
        if args.version:
            print("fake_user_agent " + VERSION)
            sys.exit()
        if args.remove:
            rm_cache()
            sys.exit()
        if args.debug:
            logger.setLevel(logging.DEBUG)
        
        browser = None if not args.browser else args.browser
        use_cache = False if args.nocache else True
        result = asyncio.run(main(browser, use_cache))
        print(result) if result is not None else sys.exit(1) 

    except KeyboardInterrupt:
        print("\nStopped by user.")
