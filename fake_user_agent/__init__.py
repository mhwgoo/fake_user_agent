"Randomly generates a useragent for fetching a web page without a browser."

from .user_agent import (
    user_agent,
    rm_tempfile,
)
from .settings import VERSION

__version__ = VERSION
