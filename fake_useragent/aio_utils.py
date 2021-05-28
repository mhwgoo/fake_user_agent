import os
import sys
import re
import json
import random
from time import sleep
from urllib.parse import quote_plus
from collections import defaultdict
import threading
import asyncio
import aiohttp
from aiohttp import ClientSession
from lxml import etree

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fake_useragent import settings
from fake_useragent.log import logger
from fake_useragent.errors import FakeUserAgentError


async def fetch(url, session):
    attempt = 0
    while True:
        async with session.get(
            url, timeout=settings.HTTP_TIMEOUT, verify_ssl=False
        ) as resp:
            # try/except block should be inside async with context manager, or it'll break
            try:
                attempt += 1
                result = await resp.text()
            except aiohttp.ServerTimeoutError:
                logger.exception("Error occurred during fetching %s", url)
                if attempt == settings.HTTP_RETRIES:
                    raise FakeUserAgentError("Maximum amount of retries reached")
                else:
                    logger.info("Sleeping for %s seconds", settings.HTTP_DELAY)
                    sleep(settings.HTTP_DELAY)
            except Exception:
                logger.exception("Error occurred during fetching %s", url)
            else:
                return result


all_versions = defaultdict(list)


async def parse(browser, session):
    html_str = await fetch(
        settings.BROWSER_BASE_PAGE.format(browser=quote_plus(browser)), session
    )
    lxml_element = etree.HTML(html_str)
    versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[
        : settings.BROWSERS_COUNT_LIMIT
    ]
    all_versions[browser].extend(versions)


async def load():
    async with ClientSession() as session:
        tasks = []
        for browser in settings.BROWSERS.keys():
            tasks.append(parse(browser, session))
        await asyncio.gather(*tasks)
        return all_versions


def write(path, data):
    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)


def read(path):
    with open(path, encoding="utf-8", mode="rt") as f:
        cache_data = f.read()
        return json.loads(cache_data)


def fetch_server():
    try:
        server_data = fetch(settings.CACHE_SERVER)
        server_data = json.loads(data)
    except (TypeError, ValueError):
        raise FakeUserAgentError("Can not load data from cache server")
    return server_data


def random_choose(browser=None, use_cache=True):
    try:
        if use_cache:
            path = settings.DB
            if os.path.isfile(path):
                data = read(path)
            else:
                data = asyncio.run(load())
                t = threading.Thread(target=write, args=(path, data))
                t.start()

        else:
            data = asyncio.run(load())
    except Exception:
        logger.warning(
            "Problem happened. Switch to fetching backup data from server %s",
            settings.CACHE_SERVER,
        )
        data = fetch_server()["browsers"]

    # Equivalent to browser is not None and browser != ""
    if browser:
        if not isinstance(browser, str):
            raise FakeUserAgentError("Please input a valid browser name")
        browser = browser.strip().lower()
        browser = settings.SHORTCUTS.get(browser, browser)
        if browser not in list(settings.BROWSERS.keys()):
            raise FakeUserAgentError("This browser is not supported.")
        print(random.choice(data[browser]))

    else:
        browser = random.choices(
            list(settings.BROWSERS.keys()),
            weights=list(settings.BROWSERS.values()),
            k=1,
        )[0]
        print(random.choice(data[browser]))


if __name__ == "__main__":
    input = input("Input a browser name or hit <enter> not to specify browser: ")
    random_choose(input)
