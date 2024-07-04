import sys
import json
import random
import asyncio
import aiohttp
from urllib.parse import quote_plus
from lxml import etree  # type: ignore

import logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s.%(filename)s[%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__package__)


VERSION = "2.3.0"
BACKUP_FILE = f"fake_useragent_{VERSION}.json"
FIXED_UA = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36"

BROWSERS = ['chrome', 'edge', 'firefox', 'safari', 'opera']
RANDOM_CUM_WEIGHTS = [80, 86, 93, 97, 100]


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
        except aiohttp.ServerTimeoutError as error:
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


async def dump():
    async with aiohttp.ClientSession() as session:
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
    try:
        with open(BACKUP_FILE, encoding="utf-8", mode="wt") as f:
            f.write(dumped)
    except Exception as error:
        logger.error(f'WRITING <{BACKUP_FILE}> failed: {error.__class__.__name__}: {error}')
    else:
        logger.debug(f"Data has been stored in <{BACKUP_FILE}>\n")


def load_and_random(browser):
    try:
        with open(BACKUP_FILE, encoding="utf-8") as f:
            data = f.read()
    except Exception as error:
        logger.debug(f'Opening <{BACKUP_FILE}> failed: {error.__class__.__name__}: {error}')
        logger.debug(f'Resort to a fixed useragent: {FIXED_UA}')
        return FIXED_UA
    else:
        logger.debug(f"Read <{BACKUP_FILE}> successfully.")
        ua = random.choice(json.loads(data)[browser])
        logger.debug(f'Randomized a useragent from <{BACKUP_FILE}>')
        return ua


async def main(browser=None, use_cache=True):
    if browser is None:
        logger.debug("A browser will be randomly given.")
        browser = random.choices(BROWSERS, weights=RANDOM_CUM_WEIGHTS, k=1)[0]
        logger.debug(f'Got "{browser}"')
    else:
        logger.debug(f'You gave "{browser}"')
        browser = browser.strip().lower()
        if browser not in BROWSERS:
            new_browser = random.choices(BROWSERS, weights=RANDOM_CUM_WEIGHTS, k=1)[0]
            logger.debug(f'"{browser}" not supported, should be one of {BROWSERS}. Randomized "{new_browser}"')

    if not use_cache:
        async with aiohttp.ClientSession() as session:
            (browser, versions) = await parse(browser, session)
            if versions is None:
                logger.debug("Reading backup data ...")
                return load_and_random(browser)
            else:
                ua = random.choice(versions)
                logger.debug("Randomized a useragent without using cache.")
                return ua 
    else:
        return load_and_random(browser)


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
    parser.add_argument("-d", "--debug", action="store_true", help="randomize a useragent in debug mode")
    parser.add_argument("-n", "--nocache", action="store_true", help="randomize a useragent by fetching the web")
    parser.add_argument("-v", "--version", action="store_true", help="print the current version of the program")
    args = parser.parse_args()
    try:
        if args.version:
            print("fake_user_agent " + VERSION)
            sys.exit()
        if args.debug:
            logger.setLevel(logging.DEBUG)
        
        browser = None if not args.browser else args.browser
        use_cache = False if args.nocache else True
        result = asyncio.run(main(browser, use_cache))
        print(result)

    except KeyboardInterrupt:
        print("\nStopped by user.")
