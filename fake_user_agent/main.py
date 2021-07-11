"""Main script to randomly generate a fake useragent using asyncio"""
import os
import json
import random
import time
from time import sleep
from urllib.parse import quote_plus
from collections import defaultdict
import asyncio
import aiohttp
from aiohttp import ClientSession
from lxml import etree

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fake_user_agent import settings
from fake_user_agent.log import logger
from fake_user_agent.errors import FakeUserAgentError


all_versions = defaultdict(list)


async def fetch(url, session):
    attempt = 0
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36"
    }

    while True:
        if attempt == settings.HTTP_RETRIES:
            raise FakeUserAgentError("Maximum amount of retries reached")

        try:
            async with session.get(
                url, headers=headers, timeout=settings.HTTP_TIMEOUT, ssl=False
            ) as resp:
                attempt += 1
                result = await resp.text()
        except asyncio.TimeoutError:
            logger.error("Timed out during fetching %s. Retrying...", url)
            sleep(settings.HTTP_DELAY)
        except aiohttp.client_exceptions.ClientOSError:
            logger.error("%s terminated connection. Retrying...", url)
            sleep(settings.HTTP_DELAY)
        except Exception:
            logger.exception("Error occurred during fetching %s.", url)
        else:
            return result


async def parse(browser, session):
    global all_versions
    html_str = await fetch(
        settings.BROWSER_BASE_PAGE.format(browser=quote_plus(browser)), session
    )
    if html_str:
        lxml_element = etree.HTML(html_str)
        versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[
            : settings.BROWSERS_COUNT_LIMIT
        ]
        all_versions[browser].extend(versions)


def write(path, data):
    rm_tempfile()
    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)


def read(path):
    with open(path, encoding="utf-8", mode="rt") as f:
        cache_data = f.read()
        return json.loads(cache_data)


def rm_tempfile():
    tempfile_list = settings.TEMP_FILE
    if tempfile_list:
        for i in tempfile_list:
            os.remove(i)
    else:
        return


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


async def main(browser=None, use_tempfile=True):
    if browser:
        if not isinstance(browser, str):
            raise FakeUserAgentError("Please give a valid browser name")
        browser = browser.strip().lower()
        browser = settings.SHORTCUTS.get(browser, browser)
        if browser not in list(settings.BROWSERS.keys()):
            raise FakeUserAgentError("This browser is not supported.")

    if settings.TEMP_FILE:
        data = read(settings.TEMP_FILE[-1])
        return random_choose(browser, data)

    else:
        async with ClientSession() as session:
            tasks = []
            for BROWSER in settings.BROWSERS.keys():
                tasks.append(parse(BROWSER, session))
            await asyncio.gather(*tasks)
            if use_tempfile:
                write(settings.DB, all_versions)
            return random_choose(browser, all_versions)


# Get user agent from terminal
def get_input():
    browser = input("Input a browser name or hit <enter> not to specify browser: ")
    print(asyncio.run(main(browser=browser, use_tempfile=True)))


# Get user agent by script import
def user_agent(browser=None, use_tempfile=True):
    return asyncio.run(main(browser, use_tempfile))
