"""Main script to randomly generate a fake useragent using asyncio"""
import os
import sys
import json
import random
from time import sleep
from urllib.parse import quote_plus
from collections import defaultdict
import asyncio
import aiohttp
from aiohttp import ClientSession
from lxml import etree

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fake_user_agent import settings
from fake_user_agent.log import logger
from fake_user_agent.errors import FakeUserAgentError


all_versions = defaultdict(list)


async def fetch(url, session):
    attempt = 0
    while True:
        try:
            async with session.get(
                url, timeout=settings.HTTP_TIMEOUT, ssl=False
            ) as resp:
                attempt += 1
                result = await resp.text()
        except asyncio.TimeoutError:
            logger.error("Error occurred during fetching %s", url)
            if attempt == settings.HTTP_RETRIES:
                raise FakeUserAgentError("Maximum amount of retries reached")
            else:
                logger.info("Sleeping for %s seconds", settings.HTTP_DELAY)
                sleep(settings.HTTP_DELAY)
        else:
            return result


async def parse(browser, session):
    global all_versions
    try:
        html_str = await fetch(
            settings.BROWSER_BASE_PAGE.format(browser=quote_plus(browser)), session
        )
    except Exception:
        all_versions = await fetch(settings.CACHE_SERVER)["browsers"]
    else:
        lxml_element = etree.HTML(html_str)
        versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[
            : settings.BROWSERS_COUNT_LIMIT
        ]
        all_versions[browser].extend(versions)


def write(path, data):
    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)


def read(path):
    with open(path, encoding="utf-8", mode="rt") as f:
        cache_data = f.read()
        return json.loads(cache_data)


def random_choose(browser, data):
    if browser:
        return random.choice(data[browser])

    else:
        browser = random.choices(
            list(settings.BROWSERS.keys()),
            weights=list(settings.BROWSERS.values()),
            k=1,
        )[0]
        return random.choice(data[browser])


async def main(browser=None):
    if browser:
        if not isinstance(browser, str):
            raise FakeUserAgentError("Please give a valid browser name")
        browser = browser.strip().lower()
        browser = settings.SHORTCUTS.get(browser, browser)
        if browser not in list(settings.BROWSERS.keys()):
            raise FakeUserAgentError("This browser is not supported.")

    if os.path.isfile(settings.DB):
        data = read(settings.DB)
        return random_choose(browser, data)

    else:
        async with ClientSession() as session:
            tasks = []
            for BROWSER in settings.BROWSERS.keys():
                tasks.append(parse(BROWSER, session))
            await asyncio.gather(*tasks)
            write(settings.DB, all_versions)
            return random_choose(browser, all_versions)


# Get user agent from terminal
def get_input():
    browser = input("Input a browser name or hit <enter> not to specify browser: ")
    print(asyncio.run(main(browser=browser)))


# Get user agent by script import
def user_agent(browser=None):
    return asyncio.run(main(browser=browser))
