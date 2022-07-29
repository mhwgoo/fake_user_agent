"""Main script to randomly generate a fake useragent."""

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

all_versions = defaultdict(list) # a dict created with its values being list

OP = ["FETCHING", "PARSING"]

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
        except Exception as e:
            attempt = call_on_error(e, url, attempt, OP[0])
        else:
            logger.debug(f"{url} has been fetched successfully.")
            return result

def call_on_error(error, url, attempt, op):
    """Retry mechanism when an error occurs."""

    attempt += 1
    logger.debug(
        "%s HTML from %s %d times",
        op,
        url,
        attempt,
    )
    if attempt == 3:
        logger.debug("Maximum %s retries reached. Exit", op)
        logger.error(str(error))
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
            versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[: settings.BROWSERS_COUNT_LIMIT]
        except Exception as e:
            attempt = call_on_error(e, url, attempt, OP[1])
        else:
            if not versions:
                attempt = call_on_error(FakeUserAgentError("Nothing parsed out"), url, attempt, op[1])

            logger.debug(f"{browser} has been parsed successfully.\n")
            return versions

async def write_to_dict(browser, session):
    """Write versions to the `all_versions` dict {browser:versions}."""

    global all_versions
    versions = await parse(browser, session)
    all_versions[browser].extend(versions) # add each element of versions list to the end of the list to be extended 
    logger.debug(f"{browser} versions has been written to all_versions.")

def write(path, data):
    """Write a json tempfile as cache if there isn't one, or update it if any. """
    
    global TEMP_FILE
    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)

    logger.debug(f"Cache has been stored in {path}.\n")
    TEMP_FILE = path

def read(path):
    """Read from a json file into a python object. Here the object is a dict."""

    with open(path, encoding="utf-8", mode="rt") as f:
        cache_data = f.read()

    logger.debug(f"Read {path} successfully.\n")
    return json.loads(cache_data)

def rm_tempfile():
    """Remove the tempfile as cache if any."""

    global TEMP_FILE
    if not TEMP_FILE:
        print("No tempfile found to be deleted.")
        return

    os.remove(TEMP_FILE)
    
    file_name = TEMP_FILE.split("/")[-1]
    print(f"{file_name} has been removed successfully.")

    TEMP_FILE = ""     

def get_browser(browser):
    """If browser name is not given, randomly choose one browser based on weights set in settings.BROWSERS."""

    if not browser:
        logger.debug(f"A browser will be randowly given.")
        browser = random.choices(
            list(settings.BROWSERS.keys()),
            weights=list(settings.BROWSERS.values()),
            k=1,
        )[0]

    else:
        logger.debug(f"{browser} will be formatted.")
        if not isinstance(browser, str):
            raise FakeUserAgentError("Browser name must be string.")
        browser = browser.strip().lower()
        browser = settings.SHORTCUTS.get(browser, browser)
        if browser not in list(settings.BROWSERS.keys()): # transform an iterator to a list
            raise FakeUserAgentError(f"{browser} is not supported.")

    return browser 
    

# ----------main----------

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_at = time.time()
        f = func(*args, **kwargs)
        time_taken = round((time.time() - start_at), 4)
        print("Time taken: {} seconds".format(time_taken))
        return f

    return wrapper

async def main(browser=None, use_tempfile=True):
    browser = get_browser(browser)
    logger.debug(f"Got {browser}.")

    if not use_tempfile :
        async with ClientSession() as session:
            versions = await parse(browser, session)
            return random.choice(versions)
    else:
        if TEMP_FILE:
            data = read(TEMP_FILE)
            return random.choice(data[browser])
        else:
            async with ClientSession() as session:
                tasks = []
                for b in settings.BROWSERS.keys():
                    tasks.append(write_to_dict(b, session))
                await asyncio.gather(*tasks)

                write(settings.DB, all_versions)
                return random.choice(all_versions[browser])

@timer
def get_input():
    """Entry point for running fakeua binary on terminal."""
    
    args = parse_args()

    try:
        if args.version:
            print("fake_user_agent " + settings.version)
            sys.exit()

        if args.remove:
            rm_tempfile()
            sys.exit()

        if args.debug:
            logger.setLevel(logging.DEBUG)
            
        browser = args.browser
        
        if args.nocache:
            print(asyncio.run(main(browser=browser, use_tempfile=False)))
        else:
            print(asyncio.run(main(browser=browser, use_tempfile=True)))

    except KeyboardInterrupt:
        print("\nStopped by user.")

def user_agent(browser=None, use_tempfile=True):
    """Entry point for getting a user agent by importing this function in a python script."""

    return asyncio.run(main(browser, use_tempfile))


if __name__ == "__main__":
    import settings
    import log
    from errors import FakeUserAgentError
    from parse import parse_args

    TEMP_FILE = settings.TEMP_FILE
    get_input()
   

else:
    from . import settings
    from . import log
    from .errors import FakeUserAgentError
    from .parse import parse_args

    TEMP_FILE = settings.TEMP_FILE

