"""setting static data"""

import os
import tempfile
import re
import platform
import glob

from fake_user_agent import __version__


DB = os.path.join(
    tempfile.gettempdir(), "fake_useragent_{version}.json".format(version=__version__)
)


def find_tempfile(dir):
    temp = []
    for root, dirs, files in os.walk(dir):
        for f in files:
            if re.search(r'^fake_useragent_', f):
                temp.append(os.path.join(dir, f))
    return temp


if platform.system() == "Windows":
    TEMP_FILE = find_tempfile(tempfile.gettempdir())
else:
    TEMP_FILE = glob.glob(os.path.join(tempfile.gettempdir(), "fake_useragent_*"))


BROWSER_BASE_PAGE = (
    "http://useragentstring.com/pages/useragentstring.php?name={browser}"  # noqa
)

BROWSERS_COUNT_LIMIT = 50

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
    "msie": "edge",
    "msedge": "edge",
    "google": "chrome",
    "googlechrome": "chrome",
    "ff": "firefox",
}


HTTP_TIMEOUT = 10

HTTP_RETRIES = 3

HTTP_DELAY = 0.1
