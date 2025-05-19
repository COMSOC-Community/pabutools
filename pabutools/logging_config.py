# logging_config.py

import logging
import os

# Create a named logger for the PB-EAR module
logger = logging.getLogger("PB-EAR")
logger.setLevel(logging.DEBUG)  # Log all levels DEBUG and above (INFO, WARNING, etc.)

os.makedirs("logs", exist_ok=True)
# Only configure handlers if not already set (avoids duplication when imported multiple times)

    # Ensure 'logs/' directory exists


    # File handler: logs all DEBUG+ messages to a file
file_handler = logging.FileHandler("logs/pb_ear.log", mode="w", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
file_handler.setFormatter(file_formatter)

    # Console handler: logs INFO+ by default, or WARNING+ if running under pytest
console_handler = logging.StreamHandler()
if os.getenv("PYTEST_CURRENT_TEST"):
    console_handler.setLevel(logging.WARNING)  # Silence INFO logs during pytest
else:
        console_handler.setLevel(logging.INFO)

console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)

    # Add both handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)
