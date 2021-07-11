"""setting static data"""

import os
import glob
import tempfile

from fake_user_agent import __version__


DB = os.path.join(
    tempfile.gettempdir(), "fake_useragent_{version}.json".format(version=__version__)
)

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
    "edge": "edge",
    "google": "chrome",
    "googlechrome": "chrome",
    "ff": "firefox",
}

OVERRIDES = {
    "Edge/IE": "Internet Explorer",
    "IE/Edge": "Internet Explorer",
}

HTTP_TIMEOUT = 10

HTTP_RETRIES = 3

HTTP_DELAY = 0.1
