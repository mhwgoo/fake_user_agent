"""Setting static data."""

import os
import tempfile
import re

from fake_user_agent import __version__

def find_tempfile(dir):
    for _, _, files in os.walk(dir):
        for f in files:
            match = re.search(r'^fake_useragent_', f)
            if match:
                return os.path.join(dir, f)
    return None

TEMP_DIR = tempfile.gettempdir()   
DB = os.path.join(TEMP_DIR, "fake_useragent_{version}.json".format(version=__version__))
TEMP_FILE = find_tempfile(TEMP_DIR)  # Windows compliant
# TEMP_FILE = glob.glob(os.path.join(TEMP_DIR, "fake_useragent_*"))

BROWSER_BASE_PAGE = "http://useragentstring.com/pages/useragentstring.php?name={browser}"
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
