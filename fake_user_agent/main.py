"""Generate fake useragent using threading. This is only for offering another solution. Not actually called in the published pkg"""
import os
import sys
import json
import random
from time import sleep
import concurrent.futures
from threading import Thread
import requests
from requests import exceptions
from urllib.parse import quote_plus
from collections import defaultdict

from lxml import etree

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fake_user_agent import settings
from fake_user_agent.log import logger
from fake_user_agent.errors import FakeUserAgentError

all_versions = defaultdict(list)


def fetch(url):
    attempt = 0
    while True:
        with requests.Session() as s:
            attempt += 1
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36"
            }
            s.headers.update(headers)

            try:
                r = s.get(url, timeout=settings.HTTP_TIMEOUT)
            except exceptions.SSLError:
                r = s.get(url, timeout=settings.HTTP_TIMEOUT, verify=False)
                return r.text
            except exceptions.ConnectTimeout:
                logger.error("Error occurred during fetching %s", url)

                if attempt == settings.HTTP_RETRIES:
                    raise FakeUserAgentError("Maximum amount of retries reached")
                else:
                    logger.debug("Sleeping for %s seconds", settings.HTTP_DELAY)
                    sleep(settings.HTTP_DELAY)
            except Exception:
                logger.exception("Error occurred during fetching %s", url)

            else:
                return r.text


def parse(browser):
    html_str = fetch(settings.BROWSER_BASE_PAGE.format(browser=quote_plus(browser)))
    lxml_element = etree.HTML(html_str)
    versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[
        : settings.BROWSERS_COUNT_LIMIT
    ]
    all_versions[browser].extend(versions)


def load():
    threads = [
        Thread(target=parse, args=(browser,)) for browser in settings.BROWSERS.keys()
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


# NOTE: load() threadpool version, haven't used
def load_by_threadpool(use_cache_server=True):
    all_versions = {}
    # Without max_workers, it's the slowest, because it has to compute it
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_browser = {
            executor.submit(get_browser_versions, browser): browser
            for browser in settings.BROWSERS.keys()
        }
        for future in concurrent.futures.as_completed(future_to_browser):
            browser = future_to_browser[future]
            data = future.result()
            all_versions[browser] = data

    return all_versions


def write(path, data):
    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)


def read(path):
    with open(path, encoding="utf-8", mode="rt") as f:
        data = f.read()
        return json.loads(data)


def random_choose(browser, data):
    if browser:
        print(random.choice(data[browser]))

    else:
        browser = random.choices(
            list(settings.BROWSERS.keys()),
            weights=list(settings.BROWSERS.values()),
            k=1,
        )[0]
        print(random.choice(data[browser]))


def main(browser):
    if browser:
        if not isinstance(browser, str):
            raise FakeUserAgentError("Please input a valid browser name")
        browser = browser.strip().lower()
        browser = settings.SHORTCUTS.get(browser, browser)
        if browser not in list(settings.BROWSERS.keys()):
            raise FakeUserAgentError("This browser is not supported.")

    if os.path.isfile(settings.DB):
        data = read(settings.DB)
        random_choose(browser, data)

    else:
        load()
        random_choose(browser, all_versions)
        write(settings.DB, all_versions)


if __name__ == "__main__":
    browser = input("Input a browser name or hit <enter> not to specify browser: ")
    main(browser=browser)
