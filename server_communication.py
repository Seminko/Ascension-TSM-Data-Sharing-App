# %% LOCAL IMPORTS

import get_endpoints
from config import REQUEST_TIMEOUT, HTTP_TRY_CAP, VERSION, SEPARATOR, ADAPTER
from logger_config import logger
from toast_notification import create_update_notification # this needs to be before get_wft_folder (if I remember correctly)

# %% MODULE IMPORTS

import re
import requests
import sys

# %% FUNCTIONS

current_tries = {"upload_tries": 0, "download_tries": 0, "check_version_tries": 0, "set_user_tries": 0, "set_download_stats_tries": 0}
session = requests.Session()
session.mount("https://", ADAPTER)
session.mount("http://", ADAPTER)

def check_for_new_versions():
    version_list = get_version_list()
    if version_list:
        newest_version = sorted(list(version_list), reverse=True)[0]
        newer_versions = {k: v for k, v in version_list.items() if k > VERSION}
        if newer_versions:
            logger.debug(f"""There are several newer versions: '{", ".join(newer_versions)}'""")
            if any([k for k, v in newer_versions.items() if v]):
                create_update_notification(mandatory=True)
                logger.critical("There is a MANDATORY update for this app. Please download the latest release (EXE) here: 'https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/releases'")
                input("Press any key to close the console")
                sys.exit()
            else:
                create_update_notification(mandatory=False)
                logger.critical("There is an optional update for this app. You can download the latest release (EXE) here: 'https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/releases'")
            logger.info(SEPARATOR)
        else:
            logger.debug(f"Current version {VERSION} is the most up-to-date")
            logger.debug(SEPARATOR)
        return newest_version
    return None

def generate_chunks(file_object, chunk_size=1024):
    while True:
        chunk = file_object.read(chunk_size)
        if not chunk:
            break
        yield chunk

def get_data_from_server():
    return make_http_request("get_data_from_server")

def get_version_list():
    return make_http_request("check_version")

def make_http_request(purpose, data_to_send=None):
    if purpose == "send_data_to_server":
        init_debug_log = "Sending data to server"
        fail_debug_log = "Sending to DB failed"
        current_tries_key = "upload_tries"
        url = get_endpoints.get_upload_endpoint()
        request_eval_str = f"session.post('{url}', data=generate_chunks(data_to_send), timeout={REQUEST_TIMEOUT}, stream=True)"
    elif purpose == "get_data_from_server":
        init_debug_log = "Downloading data from server"
        fail_debug_log = "Downloading from DB failed"
        current_tries_key = "download_tries"
        url = get_endpoints.get_download_endpoint()
        request_eval_str = f"session.get('{url}', timeout={REQUEST_TIMEOUT})"
    elif purpose == "check_version":
        init_debug_log = "Checking what is the most up-to-date version"
        fail_debug_log = "Check most up-to-date version failed"
        current_tries_key = "check_version_tries"
        url = get_endpoints.get_version_endpoint()
        request_eval_str = f"session.get('{url}', timeout={REQUEST_TIMEOUT})"
    elif purpose == "set_user":
        init_debug_log = "Setting Discord User ID and Nickname"
        fail_debug_log = "Setting Discord User ID and Nickname failed"
        current_tries_key = "set_user_tries"
        url = get_endpoints.get_set_user_endpoint()
        request_eval_str = f"session.post('{url}', json=data_to_send, timeout={REQUEST_TIMEOUT})"
    elif purpose == "set_download_stats":
        init_debug_log = "Sending successful download to stats"
        fail_debug_log = "Sending successful download to stats failed"
        current_tries_key = "set_download_stats_tries"
        url = get_endpoints.get_download_stats_endpoint()
        request_eval_str = f"session.post('{url}', json=data_to_send, timeout={REQUEST_TIMEOUT})"
    else:
        raise TypeError("make_http_request purpose is not recognized")
    
    logger.debug(init_debug_log)
    try:
        with eval(request_eval_str) as response:
            if response.status_code == 200:
                current_tries[current_tries_key] = 0
            elif response.status_code == 400:
                logger.debug(f"{process_response_text(response.text)}")
            else:
                logger.debug(f"Status code: {response.status_code}")
    
            response.raise_for_status()
            response_json = response.json()
    except Exception as e:
        logger.debug(fail_debug_log)
        current_tries[current_tries_key] += 1
        if current_tries[current_tries_key] > HTTP_TRY_CAP:
            raise type(e)(get_endpoints.remove_endpoint_from_str(e)) from None
        return None
    
    return response_json

def process_response_text(response_text):
    new_line_double_space_regex = r"(?:\n+|\s\s+)"
    html_css_regex = r'(?:[a-zA-Z0-9-_.]+\s\{.*?\}|\\(?=)|<style>.*<\/style>|<[^<]+?>|^\"|Something went wrong :-\(\s*\.?\s*)'
    return re.sub(new_line_double_space_regex, " ", re.sub(html_css_regex, '', response_text)).strip()

def send_data_to_server(data_to_send):
    return make_http_request("send_data_to_server", data_to_send)

def set_download_stats(data_to_send):
    return make_http_request("set_download_stats", data_to_send)

def set_user(data_to_send):
    return make_http_request("set_user", data_to_send)