"Randomly generates a useragent for fetching a web page without a browser."

from .user_agent import (
    user_agent,
    rm_tempfile,
)  # for convenience, only need `from fake_user_agent import user_agent, rm_tempfile`, without the module name specified in the import path
from .settings import version

__version__ = version
