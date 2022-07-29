"Randomly generates a useragent for fetching a web page without a browser."

from .main import user_agent, rm_tempfile  # for api importing convenience, only need `from fake_user_agent import user_agent, rm_tempfile`, without `main` specified
from .settings import version

__version__ = version
