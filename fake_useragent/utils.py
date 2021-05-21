import os
import sys
import re
import json
import inspect
import contextlib
import ssl
import random
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote_plus
from time import sleep

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fake_useragent import settings
from fake_useragent.log import logger
from fake_useragent.errors import FakeUserAgentError

urlopen_args = inspect.getfullargspec(urlopen).kwonlyargs
urlopen_has_ssl_context = "context" in urlopen_args


def get(url, verify_ssl=True):
    attempt = 0

    while True:
        request = Request(url)
        attempt += 1
        try:
            # url with https
            if urlopen_has_ssl_context:
                if not verify_ssl:
                    # opt out of certificate verification on a single connection
                    context = ssl._create_unverified_context()
                else:
                    context = None
                with contextlib.closing(
                    urlopen(request, timeout=settings.HTTP_TIMEOUT, context=context)
                ) as response:
                    return response.read()
            # url with http without s
            else:
                with contextlib.closing(
                    urlopen(request, timeout=settings.HTTP_TIMEOUT)
                ) as response:
                    return response.read()
        except (URLError, OSError) as e:
            logger.debug("Error occurred during fetching %s", url, exc_info=e)

            if attempt == settings.HTTP_RETRIES:
                raise FakeUserAgentError("Maximum amount of retries reached")
            else:
                logger.debug("Sleeping for %s seconds", settings.HTTP_DELAY)
                sleep(settings.HTTP_DELAY)


# This func is time-consuming, only for a small static piece of data
# You scrape the whole page, only for one two line of data in it
# Not worth it in term of getting a random useragent
# def get_browsers():
#    """
#    very hardcoded/dirty re/split stuff, but no dependencies
#
#    """
#    html = get(settings.BROWSERS_STATS_PAGE)
#    html = html.decode("utf-8")
#    html = html.split('<table class="w3-table-all notranslate">')[1]
#    html = html.split("</table")[0]
#
#    pattern = r'\.asp">(.+?)<'
#    # NOTE: re.findall returns stuff in () group, re.finditer return the whole string
#    # >>> x ='<td class="right"> 80.7 %</td>'
#    # >>> pattern = r'td\sclass="right">(.+?)\s'
#    # >>> re.findall(pattern, x))
#    # [' 80.7']
#    # >>> re.finditer(pattern, x))
#    # <callable_iterator object at 0x10b164f10>
#    # >>> for i in re.finditer(pattern, x):
#    # ...     print(i)
#    # <re.Match object; span=(1, 24), match='td class="right"> 80.7 '>
#    browsers = re.findall(pattern, html)
#
#    # dict.get(key, default=None)
#    # settings.OVERRIDES don't take effect because browsers scraped without Edge/IE
#    browsers = [settings.OVERRIDES.get(browser, browser) for browser in browsers]
#
#    pattern = r'td\sclass="right">(.+?)\s'
#    browsers_stats = re.findall(pattern, html)
#
#    # NOTE: when len(x) = 4, len(y) = 100, len(list(zip(x, y))) = 4, the first 4s
#    return list(zip(browsers, browsers_stats))


def get_browser_versions(browser):
    html = get(settings.BROWSER_BASE_PAGE.format(browser=quote_plus(browser)))
    html = html.decode("iso-8859-1")

    # split on 'some string', you get a list of strings without 'some string'
    html = html.split("<div id='liste'>")[1]
    html = html.split("</div>")[0]

    pattern = r"\?id=\d+\'>(.+?)</a"
    browsers_iter = re.finditer(pattern, html)

    browsers = []

    for browser in browsers_iter:
        if "more" in browser.group(1).lower():
            continue

        browsers.append(browser.group(1))

        if len(browsers) == settings.BROWSERS_COUNT_LIMIT:
            break

    if not browsers:
        raise FakeUserAgentError("No browsers version found for %s" % browser)

    return browsers


def get_cache_server():
    try:
        data = get(settings.CACHE_SERVER)
        data = json.loads(data)
    except (TypeError, ValueError):
        raise FakeUserAgentError("Can not load data from cache server")
    return data


def load(use_cache_server=True):
    # keep the prior data structure, backward compatible with data from cache server
    browsers_dict = {}

    try:
        for browser in settings.BROWSERS.keys():
            browsers_dict[browser] = get_browser_versions(browser)

    except Exception as exc:
        if not use_cache_server:
            raise exc  # if raise is hit, nothing will execute under raise lien

        logger.warning(
            "Error occurred during loading data."  # logging Message
            "Trying to use cache server %s",
            settings.CACHE_SERVER,  # logging Argument
            exc_info=exc,  # logging exc_info, a.k.a traceback
        )
        return get_cache_server()

    else:
        result = {"browsers": browsers_dict}
        return result


def write(path, data):
    with open(path, encoding="utf-8", mode="wt") as f:
        dumped = json.dumps(data)
        f.write(dumped)


def read(path):
    with open(path, encoding="utf-8", mode="rt") as f:
        data = f.read()
        return json.loads(data)


def get_fake_useragent(browser=None, use_cache=True):
    if use_cache:
        path = settings.DB
        # if os.path.isfile(path) & os.path.getsize(path) > 0:  ---> this check took nearly 10s
        if os.path.isfile(path):
            data = read(path)
        else:
            write(path, load())
            data = read(path)
    else:
        data = load()

    browsers = data["browsers"]

    if browser is not None and browser != "":
        if not isinstance(browser, str):
            raise FakeUserAgentError("Please input a valid browser name")
        browser = browser.strip().lower()
        browser = settings.SHORTCUTS.get(browser, browser)
        if browser not in list(browsers.keys()):
            raise FakeUserAgentError("This browser is not supported.")
        print(random.choice(browsers[browser]))

    else:
        browser = random.choices(
            list(browsers.keys()), weights=list(settings.BROWSERS.values()), k=1
        )[0]
        print(random.choice(browsers[browser]))


if __name__ == "__main__":
    input = input("Input a browser name or hit <enter> not to specify browser: ")
    get_fake_useragent(input)
