"Randomly generate a valid useragent for faking a browser."

from .user_agent import (
    user_agent,
    aio_user_agent,
    rm_cache,
    VERSION
)

__version__ = VERSION
