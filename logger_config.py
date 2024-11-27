# %% LOCAL IMPORTS

from config import SCRIPT_DIR, VERSION

# %% LOCAL IMPORTS

import logging
import os
import time

# %% FUNCTIONS

class NoExceptionFilter(logging.Filter):
    def filter(self, record):
        # If the log record is at EXCEPTION level, filter it out (return False)
        return not record.exc_info

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the overall log level to DEBUG

# Console handler with INFO level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.addFilter(NoExceptionFilter())
console_formatter = logging.Formatter('%(asctime)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Time Rotating File handler with DEBUG level
log_dir = os.path.join(SCRIPT_DIR, 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, 'ascension_tsm_data_sharing_app')

timestamp = time.strftime("%Y%m%d_%H%M%S")
log_file_with_suffix = f"{log_file}_v{VERSION}_{timestamp}"

file_handler = logging.FileHandler(f"{log_file_with_suffix}.log")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - [%(filename)s - %(funcName)s]: %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)