# %% LOCAL IMPORTS

from get_endpoints import get_latest_release_endpoint
from config import GITHUB_REPO_URL, DISCORD_INVITE_LINK

# %% MODULE IMPORTS

import logging
import os
import time
import psutil
import sys
import re
import subprocess
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# %% FUNCTIONS

VERSION = "1.0"

if getattr(sys, 'frozen', False):
    # Running in PyInstaller executable
    SCRIPT_DIR = os.path.dirname(sys.executable)
    EXE_PATH = sys.executable
else:
    # Running as a regular Python script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_PATH = os.path.abspath(__file__)

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
log_file = os.path.join(log_dir, 'updatificator')

timestamp = time.strftime("%Y%m%d_%H%M%S")
log_file_with_suffix = f"{log_file}_v{VERSION}_{timestamp}"

file_handler = logging.FileHandler(f"{log_file_with_suffix}.log")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - [%(filename)s - %(funcName)s]: %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def kill_process_by_pid(pid):
    logger.debug(f"Killing main app by pid ({pid})")
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait()
    except psutil.NoSuchProcess:
        logger.debug("Pid no longer running")
        pass
    except psutil.AccessDenied:
        logger.info("Access denied")
    
def run_main_app(main_app_exe_path):
    logger.info("Running updated main app")
    subprocess.Popen([main_app_exe_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
def download_exe(url, save_path, chunk_size=8192):
    logger.info("Downloading the latest version")
    session = requests.Session()
    session.mount("https://", ADAPTER)
    session.mount("http://", ADAPTER)
    
    sleep_coeficient = 5
    current_try = 1
    max_tries = 5
    while current_try < max_tries:
        try:
            with session.get(url, stream=True) as response:
                if response.status_code == 200:
                    with open(save_path, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            file.write(chunk)
                    return True
                else:
                    logger.debug("Update failed, status code: {response.status_code}")
                response.raise_for_status()
        except Exception as e:
            logger.debug(f"Update failed, exception: {str(repr(e))}")
            pass
        time.sleep(sleep_coeficient * current_try)
        current_try += 1
    return False

def remove_and_rename(main_app_exe_path, main_app_exe_path_temp, retries=5, delay=.5):
    for _ in range(retries):
        try:
            logger.debug(f"Removing old version of the app: '{main_app_exe_path}'")
            os.remove(main_app_exe_path)
            logger.debug(f"Re-naming new version of the app from: '{main_app_exe_path_temp}' to: '{main_app_exe_path}'")
            os.rename(main_app_exe_path_temp, main_app_exe_path)
            return
        except PermissionError:
            logger.debug("PermissionError, trying again")
            time.sleep(delay)
    raise ValueError("Even after {retries} retries, couldn't remove the original file: '{main_app_exe_path}'.")
            
if __name__ == "__main__":
    try:
        main_app_pid = int(sys.argv[1])
        main_app_exe_path = sys.argv[2]
        
        logger.debug(f"Main app pid: {main_app_pid}")
        logger.debug(f"Main app exe path: '{main_app_exe_path}'")
        
        url = get_latest_release()
        main_app_exe_path_temp = re.sub("\.exe", "_downloaded_new_version_to_be_renamed.exe", main_app_exe_path)
        if download_exe(url, main_app_exe_path_temp):
            kill_process_by_pid(main_app_pid)
            remove_and_rename(main_app_exe_path, main_app_exe_path_temp)
            run_main_app(main_app_exe_path)
        else:
            logger.info("Update failed. Give it a couple of minutes and try again.")
            input("Press Enter to close the console")
        logger.info("Update done, main app re-run, exiting updater")
    except Exception:
        logger.info(f"An exception occurred. Please send the logs to Mortificator on Discord ({DISCORD_INVITE_LINK} --> Other DEVs Addons (N-Z) --> #tsm-data-sharing - tag @Mortificator) or create an issue on Github ({GITHUB_REPO_URL}/issues)")
        logger.exception("Exception")
        input("Press Enter to close the console")