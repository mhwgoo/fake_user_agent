import logging

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s.%(filename)s[%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__package__)
