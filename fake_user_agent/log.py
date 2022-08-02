"Sets up the package level logger."

import logging

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(filename)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(
    __package__
)  # if imported, all modules will have the same logger called by name of __package__'s value'
