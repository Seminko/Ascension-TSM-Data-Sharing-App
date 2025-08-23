# %% MODULE IMPORTS

import sys
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# %% FUNCTIONS

VERSION = "1.4"

if getattr(sys, 'frozen', False):
    # Running in PyInstaller executable
    SCRIPT_DIR = os.path.dirname(sys.executable)
    EXE_PATH = sys.executable
else:
    # Running as a regular Python script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_PATH = os.path.abspath(__file__)

UPDATER_PATH = os.path.join(SCRIPT_DIR, "updatificator.exe")

XML_TASK_DEFINITION_PATH = os.path.join(SCRIPT_DIR, "startup_task_definition.xml")

JSON_FILE_NAME = "update_times.json"
JSON_PATH = os.path.join(SCRIPT_DIR, JSON_FILE_NAME)

UPLOAD_STATS_FILE_NAME = "upload_stats.json"
UPLOAD_STATS_PATH = os.path.join(SCRIPT_DIR, UPLOAD_STATS_FILE_NAME)

UPDATE_PREFERENCES_FILE_NAME = 'update_preferences.json'
UPDATE_PREFERENCES_PATH = os.path.join(SCRIPT_DIR, UPDATE_PREFERENCES_FILE_NAME)

NICKNAME_FILE_NAME = "discord_id_username.json"
NICKNAME_FILE_NAME_PATH = os.path.join(SCRIPT_DIR, NICKNAME_FILE_NAME)

MESSAGES_FILE_NAME = "handled_messages.json"
MESSAGES_FILE_PATH = os.path.join(SCRIPT_DIR, MESSAGES_FILE_NAME)

UPLOAD_INTERVAL_SECONDS = 300
DOWNLOAD_INTERVAL_SECONDS = 300
GET_MESSAGES_INTERVAL_SECONDS = 300
UPDATE_INTERVAL_SECONDS = 43200
DISCORD_ID_NICKNAME_INTERVAL_SECONDS = 86400

UPLOAD_LOOPS_PER_DOWNLOAD = DOWNLOAD_INTERVAL_SECONDS / UPLOAD_INTERVAL_SECONDS
UPLOAD_LOOPS_PER_GET_MESSAGES = GET_MESSAGES_INTERVAL_SECONDS / UPLOAD_INTERVAL_SECONDS
UPLOAD_LOOPS_PER_UPDATE = UPDATE_INTERVAL_SECONDS / UPLOAD_INTERVAL_SECONDS
UPLOAD_LOOPS_PER_DISCORD_ID_NICKNAME = discord_id_nickname_loops = DISCORD_ID_NICKNAME_INTERVAL_SECONDS / UPLOAD_INTERVAL_SECONDS

HTTP_TRY_CAP = 5
REQUEST_TIMEOUT = (60, 180)
MAX_RETRIES = 7
RETRY_STRATEGY = Retry(
    total=MAX_RETRIES,  # Retry up to 5 times
    backoff_factor=5,  # Wait 5, 10, 20, 40, 80 seconds between retries
    status_forcelist=[500, 502, 503, 504],  # Retry on these HTTP status codes
    allowed_methods=["GET", "POST"],  # Apply to these HTTP methods
    raise_on_status=False,  # Don't raise exception immediately on bad status
)
ADAPTER = HTTPAdapter(max_retries=RETRY_STRATEGY)

NUMBER_OF_LOGS_TO_KEEP = 50

APP_NAME_WITHOUT_VERSION = "Ascension TSM Data Sharing App"
APP_NAME = f"{APP_NAME_WITHOUT_VERSION} v{VERSION}"
MAIN_SEPARATOR = "==========================================================================================="
SEPARATOR = "-------------------------------------------------------------------------------------------"

GITHUB_REPO_URL = "https://github.com/Seminko/Ascension-TSM-Data-Sharing-App"
DISCORD_INVITE_LINK = "https://discord.gg/uTxuDvuHcn"

LOADING_CHARS = ["[   ]","[=  ]","[== ]","[===]","[ ==]","[  =]"]