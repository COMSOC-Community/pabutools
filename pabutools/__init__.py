import logging
import os
from pabutools.logging_config import setup_logging

__author__ = "Simon Rey, Grzegorz Pierczyński, Markus Utke and Piotr Skowron"
__email__ = "reysimon@orange.fr"
__version__ = "1.1.11"

_env_level = os.environ.get("PABUTOOLS_LOGLEVEL", "").upper()
if _env_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    setup_logging(level=getattr(logging, _env_level))
else:
    setup_logging()
