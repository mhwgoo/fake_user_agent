"""Setting static data."""

import os
import re
import tempfile

from .log import logger

VERSION = "2.1.4"

TEMP_DIR = tempfile.gettempdir()  # str type


def find_tempfile(dir):
    for _, _, files in os.walk(dir):
        for f in files:
            match = re.search(r"^fake_useragent_", f)
            if match:
                logger.debug(f"{f} is found.")
                return os.path.join(dir, f)  # str type

    logger.debug("No cache is found.")
    return ""


DB = os.path.join(
    TEMP_DIR, "fake_useragent_{version}.json".format(version=VERSION)
)  # str type

BROWSER_BASE_PAGE = (
    "http://useragentstring.com/pages/useragentstring.php?name={browser}"
)

BROWSERS = {
    "chrome": 80.7,
    "edge": 5.6,
    "firefox": 6.1,
    "safari": 3.7,
    "opera": 2.4,
}

SHORTCUTS = {
    "internet explorer": "edge",
    "ie": "edge",
    "google": "chrome",
    "googlechrome": "chrome",
    "ff": "firefox",
}

BROWSERS_COUNT_LIMIT = 50

HTTP_TIMEOUT = 10
