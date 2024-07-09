import sys
import os
import json
import random
import asyncio
from urllib.parse import quote_plus
from aiohttp import ClientSession, ServerTimeoutError
from lxml import etree  # type: ignore

import logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s.%(filename)s[%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

VERSION = "2.3.9"
FIXED_UA = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36"
CACHE_FILE = "$HOME/.cache/fakeua/fake_useragent.json"
BROWSERS = ['chrome', 'edge', 'firefox', 'safari', 'opera']
BROWSERS_CUM_WEIGHTS = [80, 86, 93, 97, 100]

def quit_on_error(file_path, error, op):
    logger.error(f'{op} <{file_path}> failed: {error.__class__.__name__}: {error}')
    sys.exit(1)


def call_on_error(error, url, attempt, op):
    attempt += 1
    logger.debug(f"{op} {url} {attempt} times")
    if attempt == 3:
        logger.debug(f"Maximum {op} reached: {error.__class__.__name__}: {error}")
    return attempt


async def parse(browser, session):
    base_page = "http://useragentstring.com/pages/useragentstring.php?name={browser}"
    url = base_page.format(browser=quote_plus(browser))
    attempt = 0
    result = None
    while True:
        try:
            async with session.get(url, headers={"User-Agent": FIXED_UA}, ssl=False) as resp:
                result = await resp.text()
                break
        except ServerTimeoutError as error:
            attempt = call_on_error(error, url, attempt, "FETCHING")
            if attempt == 3:
                break
            else:
                continue
        except Exception as error:
            logger.debug(f'FETCHING {url} failed: {error.__class__.__name__}: {error}')
            break

    if result is None:
        return (browser, None)

    lxml_element = etree.HTML(result)
    browser_num = 50
    versions = lxml_element.xpath('//*[@id="liste"]/ul/li/a/text()')[:browser_num]
    if not versions:
        logger.debug("Nothing parsed out. Check if the website has changed.")
        return (browser, None)

    logger.debug(f"{url} has been parsed successfully.")
    return (browser, versions)


async def dump(cache_path):
    async with ClientSession() as session:
        tasks = []
        for browser in BROWSERS:
            tasks.append(parse(browser, session))
        results = await asyncio.gather(*tasks)

    if not results:
        logger.error("Nothing parsed out. Check if the website has changed. Quit out.")
        sys.exit(1)

    all_browsers = {}
    for result in results:
        if result[1] is None:
            logger.error('Nothing parsed out from "{result[0]}". Quit out.')
            sys.exit(1)
        all_browsers[result[0]] = result[1]

    dumped = json.dumps(all_browsers)

    cache_path = os.path.expanduser(os.path.expandvars(cache_path))
    dir_name = os.path.dirname(cache_path)
    if not os.path.exists(dir_name):
        logger.debug(f'Directory <{dir_name}> not found. CREATING DIRECTORY...')
        try:
            os.makedirs(dir_name)
        except Exception as error:
            quit_on_error(cache_path, error, "CREATING DIRECTORY")

    try:
        with open(cache_path, encoding="utf-8", mode="wt") as f:
            f.write(dumped)
    except Exception as error:
            quit_on_error(cache_path, error, "WRITING")
    logger.debug(f"Data has been stored in <{cache_path}>\n")


def remove(cache_path):
    cache_path = os.path.expanduser(os.path.expandvars(cache_path))
    try:
        os.remove(cache_path)
    except PermissionError:
        import shutil
        try:
            shutil.rmtree(cache_path)
        except Exception as error:
            quit_on_error(cache_path, error, "REMOVING")
    except Exception as error:
        quit_on_error(cache_path, error, "REMOVING")

    logger.debug(f"<{cache_path}> has been removed successfully.\n")


async def read_and_random(browser, cache_path):
    cache_path = os.path.expanduser(os.path.expandvars(cache_path))
    if not os.path.isfile(cache_path):
        logger.debug(f"<{cache_path}> not found. LOADING cache...")
        await dump(cache_path)

    try:
        with open(cache_path, encoding="utf-8") as f:
            data = f.read()

    except Exception as error:
        logger.debug(f'Opening <{cache_path}> failed: {error.__class__.__name__}: {error}')
        logger.debug("Resort to a fixed useragent.")
        return FIXED_UA
    else:
        logger.debug(f"Read <{cache_path}> successfully.")
        ua = random.choice(json.loads(data)[browser])
        logger.debug(f'Randomized a useragent from <{cache_path}>')
        return ua


async def main(browser=None, use_cache=True, cache_path=CACHE_FILE):
    if browser is None:
        logger.debug("A browser will be randomly given.")
        browser = random.choices(BROWSERS, weights=BROWSERS_CUM_WEIGHTS, k=1)[0]
        logger.debug(f'Got "{browser}".')
    else:
        logger.debug(f'You gave "{browser}".')
        browser = browser.strip().lower()
        if browser not in BROWSERS:
            new_browser = random.choices(BROWSERS, weights=BROWSERS_CUM_WEIGHTS, k=1)[0]
            logger.debug(f'"{browser}" not supported, should be one of {BROWSERS}. Randomized "{new_browser}"')

    if not use_cache:
        async with ClientSession() as session:
            (browser, versions) = await parse(browser, session)
            if versions is None:
                logger.debug(f'FETCHING "{browser}" failed. READING <{cache_path}>...')
                return await read_and_random(browser, cache_path)
            else:
                ua = random.choice(versions)
                logger.debug("Randomized a useragent without using cache.")
                return ua
    else:
        return await read_and_random(browser, cache_path)


async def aio_user_agent(browser=None, use_cache=True, cache_path=CACHE_FILE):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        return await loop.create_task(main(browser, use_cache, cache_path))
    else:
        return asyncio.run(main(browser, use_cache, cache_path))


def user_agent(browser=None, use_cache=True, cache_path=CACHE_FILE):
    return asyncio.run(main(browser, use_cache, cache_path))


def run_on_term():
    import argparse
    parser = argparse.ArgumentParser(description="Randomly generate a valid useragent for faking a browser.")
    parser.add_argument("browser", nargs="?", default="", help="supported values: chrome, edge, firefox, safari, opera (case insensitive)")
    parser.add_argument("-n", "--nocache", action="store_true", help="randomize a useragent by fetching the web")
    parser.add_argument("-c", "--cache", nargs=1, help="randomize a useragent by using cache rather than the default one")
    parser.add_argument("-d", "--debug", action="store_true", help="randomize a useragent in debug mode")
    parser.add_argument("-l", "--load", nargs=1, help="load up-to-date useragent versions as cache to specified file path")
    parser.add_argument("-r", "--remove", nargs=1, help="remove cache at specified file path")
    parser.add_argument("-v", "--version", action="store_true", help="print the current version of the program")
    args = parser.parse_args()
    try:
        if args.version:
            print("fake_user_agent " + VERSION)
            sys.exit()
        if args.debug:
            logger.setLevel(logging.DEBUG)
        if args.load:
            asyncio.run(dump(args.load[0]))
            sys.exit()
        if args.remove:
            remove(args.remove[0])
            sys.exit()

        browser = None if not args.browser else args.browser
        use_cache = False if args.nocache else True
        if args.cache:
            if os.path.isfile(args.cache[0]):
                cache_path = args.cache[0]
            else:
                logger.debug(f"<{args.cache[0]}> not found. Resort to <{CACHE_FILE}>")
                cache_path = CACHE_FILE
        else:
            cache_path = CACHE_FILE
        result = asyncio.run(main(browser, use_cache, cache_path))
        print(result)

    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    run_on_term()
