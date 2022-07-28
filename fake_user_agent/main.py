"""Main script to randomly generate a fake useragent using asyncio"""
import os
import json
import random
import sys
from urllib.parse import quote_plus
from collections import defaultdict
from lxml import etree
# for asynchronous programming
import asyncio
from aiohttp import ClientSession

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fake_user_agent import settings
from fake_user_agent.log import logger
from fake_user_agent.errors import FakeUserAgentError
from fake_user_agent.parse import get_browser_input

all_versions = defaultdict(list) # a dict created with its values being list

OP = ["FETCHING", "PARSING"]
TEMP_FILE = settings.TEMP_FILE 

# Fetch html text file using aiohttp session.
async def fetch(url, session):
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
            if result.status != 200:  # only a 200 response has a response body
                attempt = call_on_error(result.status, url, attempt, OP[0])
            return result

# Retry mechanism
def call_on_error(error, url, attempt, op):
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

# Parse out a browser's versions 
async def parse(browser, session):
    html_str = await fetch(settings.BROWSER_BASE_PAGE.format(browser=quote_plus(browser)), session)
    lxml_element = etree.HTML(html_str)
    versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[: settings.BROWSERS_COUNT_LIMIT]
    return versions

# Write versions to the `all_versions` dict {browser:versions}.
async def write_to_dict(browser, session):
    global all_versions
    versions = await parse(browser, session)
    all_versions[browser].extend(versions) # add each element of versions list to the end of the list to be extended 

def write(path, data):
    rm_tempfile()
    global TEMP_FILE
    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)
    TEMP_FILE = settings.TEMP_FILE

# Read from a json file into a python object. Here the object is a dict.
def read(path):
    with open(path, encoding="utf-8", mode="rt") as f:
        cache_data = f.read()
        return json.loads(cache_data)

def rm_tempfile():
    global TEMP_FILE
    if TEMP_FILE is None:
        return
    os.remove(TEMP_FILE)

# If browser name is not given, randomly choose one browser based on weights set in settings.BROWSERS.
def get_browser(browser):
    if browse is None:
        browser = random.choices(
            list(settings.BROWSERS.keys()),
            weights=list(settings.BROWSERS.values()),
            k=1,
        )[0]
        return random.choice(data[browser])
    else:
        if not isinstance(browser, str):
            raise FakeUserAgentError("Browser name must be string")
        browser = browser.strip().lower()
        browser = settings.SHORTCUTS.get(browser, browser)
        if browser not in list(settings.BROWSERS.keys()): # transform a generator to a list
            raise FakeUserAgentError(f"{browser} is not supported.")
    
async def main(browser=None, use_tempfile=True):
    browser = get_browser(browser)

    if not use_tempfile :
        async with ClientSession() as session:
            versions = await parse(browser, session)
            return random.choice(versions)
    else:
        if TEMP_FILE is not None:
            data = read(TEMP_FILE)
            return random.choice(data[browser])
        else:
            async with ClientSession() as session:
                tasks = []
                tasks.append(write_to_dict(browser, session))
                await asyncio.gather(*tasks)
                write(settings.DB, all_versions)
                return random.choose(all_versions[browser])

# Display a user agent on terminal.
def get_input():
    browser = get_browser_input()
    print(asyncio.run(main(browser=browser, use_tempfile=True)))

# Get a user agent by importing this function in a python script.
def user_agent(browser=None, use_tempfile=True):
    return asyncio.run(main(browser, use_tempfile))
