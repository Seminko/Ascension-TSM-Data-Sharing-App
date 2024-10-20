# %% LOCAL IMPORTS

from toast_notification import create_update_notification, create_generic_notification # this needs to be before get_wft_folder (if I remember correctly)
from get_wtf_folder import get_wtf_folder
from hash_username import hash_username
from get_endpoints import get_upload_endpoint, get_download_endpoint, remove_endpoint_from_str, get_version_endpoint
from task_scheduler import create_task_from_xml
import luadata_serialization

# %% MODULE IMPORTS

import os
import json
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from re import sub as re_sub, search as re_search
from psutil import process_iter
import io
import sys

# %% GLOBAL VARS

VERSION = "1.1.1"
MAX_VERSION = None

if getattr(sys, 'frozen', False):
    # Running in PyInstaller executable
    SCRIPT_DIR = os.path.dirname(sys.executable)
    EXE_PATH = sys.executable
else:
    # Running as a regular Python script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_PATH = os.path.abspath(__file__)
    
XML_TASK_DEFINITION_PATH = os.path.join(SCRIPT_DIR, "startup_task_definition.xml")
    
JSON_FILE_NAME = "update_times.json"
JSON_PATH = os.path.join(SCRIPT_DIR, JSON_FILE_NAME)

UPLOAD_STATS_FILE_NAME = "upload_stats.json"
UPLOAD_STATS_PATH = os.path.join(SCRIPT_DIR, UPLOAD_STATS_FILE_NAME)

UPLOAD_INTERVAL_SECONDS = 300
DOWNLOAD_INTERVAL_SECONDS = 900
UPDATE_INTERVAL_SECONDS = 9000
HTTP_TRY_CAP = 5
current_tries = {"upload_tries": 1, "download_tries": 1, "check_version_tries": 1}
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

APP_NAME = f"Ascension TSM Data Sharing App v{VERSION}"
SEPARATOR = "---------------------------------------------"

UPLOAD_STATS_ACHIEVEMENTS = {
    3: "ACHIEVEMENT UNLOCKED! Your third upload! Steady pace, I like it!",
    10: "ACHIEVEMENT UNLOCKED! Ten uploads! Heck yea!",
    25: "ACHIEVEMENT UNLOCKED! Twenty five uploads. Respectable!",
    50: "ACHIEVEMENT UNLOCKED! Half a hundred. You rock!",
    100: "ACHIEVEMENT UNLOCKED! Hundred uploads??? Epic!",
    1000: "ACHIEVEMENT UNLOCKED! A thousand uploads. We're getting into legendary territory!",
    10000: "ACHIEVEMENT UNLOCKED! TEN THOUSAND! OK, consider yourself a LEGEND!",
    100000: "ACHIEVEMENT UNLOCKED! Hundred thousand? I mean, other players LOVE you for this, but if you continue there's gonna have to be an intervention :-P",
    1000000: "ACHIEVEMENT UNLOCKED! MEGA! I mean a million. You're now on par with the Emperor of Mankind. Something tells me we forgot about that intervention we mentioned at 100k uploads...",
    10000000: "ACHIEVEMENT UNLOCKED! TEN MILLION UPLOADS!!! Real talk, dude, you NEED to stop...",
}

# %% FUNCTIONS

def generate_chunks(file_object, chunk_size=1024):
    while True:
        chunk = file_object.read(chunk_size)
        if not chunk:
            break
        yield chunk

def process_response_text(response_text):
    new_line_double_space_regex = r"(?:\n+|\s\s+)"
    html_css_regex = r'(?:[a-zA-Z0-9-_.]+\s\{.*?\}|\\(?=)|<style>.*<\/style>|<[^<]+?>|^\"|Something went wrong :-\(\s*\.?\s*)'
    return re_sub(new_line_double_space_regex, " ", re_sub(html_css_regex, '', response_text)).strip()

def make_http_request(purpose, data_to_send=None):
    global current_tries
    if purpose == "send_data_to_server":
        init_debug_log = "Sending data to server"
        fail_debug_log = "Sending to DB failed"
        current_tries_key = "upload_tries"
        url = get_upload_endpoint()
        request_eval_str = f"session.post('{url}', data=generate_chunks(data_to_send), timeout=REQUEST_TIMEOUT, stream=True)"
    elif purpose == "get_data_from_server":
        init_debug_log = "Downloading data from server"
        fail_debug_log = "Downloading from DB failed"
        current_tries_key = "download_tries"
        url = get_download_endpoint()
        request_eval_str = f"session.get('{url}', timeout=REQUEST_TIMEOUT)"
    elif purpose == "check_version":
        init_debug_log = "Checking what is the most up-to-date version"
        fail_debug_log = "Check most up-to-date version failed"
        current_tries_key = "check_version_tries"
        url = get_version_endpoint()
        request_eval_str = f"session.get('{url}', timeout=REQUEST_TIMEOUT)"
    
    logger.debug(init_debug_log)
    try:
        with eval(request_eval_str) as response:
            if response.status_code == 200:
                current_tries[current_tries_key] = 1
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
            raise type(e)(remove_endpoint_from_str(e)) from None
        return None
    
    return response_json

def send_data_to_server(data_to_send):
    return make_http_request("send_data_to_server", data_to_send)

def get_data_from_server():
    return make_http_request("get_data_from_server")

def get_version_list():
    return make_http_request("check_version")
    
def interruptible_sleep(seconds):
    start_time = time.time()
    end_time = start_time + seconds
    
    while time.time() < end_time:
        time.sleep(0.1)  # Sleep in smaller increments

def get_files(dst_folder):
    return [f for f in os.listdir(dst_folder) if os.path.isfile(os.path.join(dst_folder, f))]

def remove_old_logs():
    logger.debug("Checking for old logs to be removed")
    dst_folder = os.path.join(SCRIPT_DIR, 'logs')
    file_list = get_files(dst_folder)
    if len(file_list) > NUMBER_OF_LOGS_TO_KEEP:
        full_path_list = [dst_folder + "\\" + i for i in file_list]
        full_path_list.sort(key=os.path.getmtime, reverse=True)
        logs_to_remove = full_path_list[NUMBER_OF_LOGS_TO_KEEP:]
        word = "logs"
        if len(logs_to_remove) == 1:
            word = "log"
        logger.debug(f"Removing {len(logs_to_remove)} oldest {word}") 
        for log_to_remove in logs_to_remove:
            try:
                os.remove(log_to_remove)
            except PermissionError as e:
                logger.debug(f"Removing log '{log_to_remove}' failed due to: '{str(repr(e))}'") 
    else:
        logger.debug("No logs to be removed")
    logger.debug(SEPARATOR)

class NoExceptionFilter(logging.Filter):
    def filter(self, record):
        # If the log record is at EXCEPTION level, filter it out (return False)
        return not record.exc_info
    
def get_logger():
    # Create a logger
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
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - [%(funcName)s]: %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def json_file_initialized():
    logger.debug("Checking if json file is initialized")
    if next((f for f in os.listdir() if f == JSON_FILE_NAME), None):
        return True
    return False

def get_latest_scans_across_all_accounts_and_realms(file_info):
    logger.debug("Getting latest scan ascross all accounts and realms")
    last_updates = [{"realm": r["realm"], "last_complete_scan": r["last_complete_scan"], "scan_data": r["scan_data"], "username": re_search(r"(?<=\\Account\\)([^\\]+)", f["file_path"])[0]} for f in file_info for r in f["realm_last_complete_scan"]]
    active_realms_unique = list(set([r["realm"] for r in last_updates]))
    latest_data = []
    for realm in active_realms_unique:
        obj = {}
        obj["realm"] = realm
        obj["last_complete_scan"] = max([r["last_complete_scan"] for r in last_updates if r["realm"] == realm])
        obj["username"] = next(r["username"] for r in last_updates if r["realm"] == realm and r["last_complete_scan"] == obj["last_complete_scan"])
        obj["scan_data"] = next(r["scan_data"] for r in last_updates if r["realm"] == realm and r["last_complete_scan"] == obj["last_complete_scan"])
        latest_data.append(obj)
    return latest_data

def initiliaze_json():
    create_task_from_xml(task_name="TSM Data Sharing App", exe_path=EXE_PATH, working_directory=SCRIPT_DIR, xml_path=XML_TASK_DEFINITION_PATH, logger=logger)
    logger.info(SEPARATOR)
    logger.info(f"Initializing '{JSON_FILE_NAME}'")
    wtf_folder = get_wtf_folder(logger)
    logger.info(f"WTF folder found at: '{wtf_folder}'")
    lua_file_paths = get_tsm_auctiondb_lua_files(wtf_folder)
    file_info = get_lua_file_path_info(lua_file_paths)
    latest_data = get_latest_scans_across_all_accounts_and_realms(file_info)
    
    logger.debug("Creating json file")
    obj = {}
    obj["wtf_path"] = wtf_folder
    obj["file_info"] = [{"file_path": f["file_path"], "last_modified": f["last_modified"]} for f in file_info]
    obj["latest_data"] = latest_data
    write_json_file(obj)
    logger.info(SEPARATOR)
    
def write_to_upload_stats(upload_dict):
    if os.path.exists(UPLOAD_STATS_PATH):
        with open(UPLOAD_STATS_PATH, "r") as outfile:
            upload_stats_str = outfile.read()
            if upload_stats_str:
                upload_stats_json = json.loads(upload_stats_str)
                if "total_upload_count" in upload_stats_json:
                    upload_stats_json["total_upload_count"] += 1
                else:
                    upload_stats_json["total_upload_count"] = 1
                
                if "total_items_updated" in upload_stats_json:
                    upload_stats_json["total_items_updated"] += upload_dict["items_updated"]
                else:
                    upload_stats_json["total_items_updated"] = upload_dict["items_updated"]
                    
                if "individual_uploads" in upload_stats_json:
                    upload_stats_json["individual_uploads"].append(upload_dict)
                else:
                    upload_stats_json["individual_uploads"] = [upload_dict]
                    
                with open(UPLOAD_STATS_PATH, "w") as outfile:
                    outfile.write(json.dumps(upload_stats_json, indent=4))
                    
                if upload_stats_json["total_upload_count"] in UPLOAD_STATS_ACHIEVEMENTS:
                    create_generic_notification("ACHIEVEMENT UNLOCKED!", f"{UPLOAD_STATS_ACHIEVEMENTS[upload_stats_json['total_upload_count']].replace('ACHIEVEMENT UNLOCKED!', '')}&#10;So far you helped update {upload_stats_json['total_items_updated']:,} items.")
                    logger.info(SEPARATOR)
                    logger.info(UPLOAD_STATS_ACHIEVEMENTS[upload_stats_json['total_upload_count']])
                    logger.info(f"So far you helped update {upload_stats_json['total_items_updated']:,} items.")
                elif upload_stats_json['total_upload_count'] % 50 == 0:
                    create_generic_notification("Steady uploader!", f"Big thanks for another 50 uploads.&#10;So far you uploaded {upload_stats_json['total_upload_count']:,} times and helped update {upload_stats_json['total_items_updated']:,} items.")
                    logger.info(SEPARATOR)
                    logger.info("Steady uploader! Big thanks for another 50 uploads.")
                    logger.info(f"So far you uploaded {upload_stats_json['total_upload_count']:,} times and helped update {upload_stats_json['total_items_updated']:,} items.")
                    
                return

    upload_stats_json = {}
    upload_stats_json["total_upload_count"] = 1
    upload_stats_json["total_items_updated"] = upload_dict["items_updated"]
    upload_stats_json["individual_uploads"] = [upload_dict]
    
    with open(UPLOAD_STATS_PATH, "w") as outfile:
        outfile.write(json.dumps(upload_stats_json, indent=4))
        
    create_generic_notification("ACHIEVEMENT UNLOCKED!", f"Your first upload! Keep it up! Proud of you!&#10;So far you helped update {upload_stats_json['total_items_updated']:,} items.")
    logger.info(SEPARATOR)
    logger.info("ACHIEVEMENT UNLOCKED! Your first upload! Keep it up! Proud of you!")
    logger.info(f"So far you helped update {upload_stats_json['total_items_updated']:,} items.")

        
def write_json_file(json_object):
    logger.debug("Saving json file")
    with open(JSON_PATH, "w") as outfile:
        json_string = json.dumps(json_object, indent=4)
        outfile.write(json_string)
        
def read_json_file():
    logger.debug("Reading json file")
    with open(JSON_PATH, "r") as outfile:
        json_object = json.loads(outfile.read())
        return json_object
    
def get_last_complete_scan(lua_file_path):
    logger.debug(f"Getting last complete scans for '{redact_account_name_from_lua_file_path(lua_file_path)}'")
    with open(lua_file_path, "r") as outfile:
        data = luadata_serialization.unserialize(outfile.read(), encoding="utf-8", multival=False)
        realm_list = []
        if "realm" in data:
            for realm in data["realm"]:
                obj = {}
                obj["realm"] = realm
                obj["last_complete_scan"] = data["realm"][realm]["lastCompleteScan"]
                obj["scan_data"] = data["realm"][realm]["scanData"]
                realm_list.append(obj)
        return realm_list

def get_lua_file_path_info(lua_file_paths):
    file_updated_list = []
    for lua_file_path in lua_file_paths:
        logger.debug(f"Getting lua file path info for '{redact_account_name_from_lua_file_path(lua_file_path)}'")
        obj = {}
        obj["file_path"] = lua_file_path
        obj["last_modified"] = os.path.getmtime(lua_file_path)
        obj["realm_last_complete_scan"] = get_last_complete_scan(lua_file_path)
        file_updated_list.append(obj)
    return file_updated_list

def get_tsm_auctiondb_lua_files(wtf_folder):
    logger.debug("Getting all lua files for all accounts")
    "Gets 'TradeSkillMaster_AuctionDB.lua' file paths for all accounts"
    account_names = os.listdir(os.path.join(wtf_folder, "Account"))
    
    found_file_path_list = []
    file_path_list = []
    for account_name in account_names:
        path = os.path.join(wtf_folder,
                            "Account",
                            account_name,
                            "SavedVariables",
                            "TradeSkillMaster_AuctionDB.lua")
        file_path_list.append(path)
        if os.path.isfile(path):
            found_file_path_list.append(path)
            
    if found_file_path_list:
        return found_file_path_list
    else:
        raise ValueError(f"Couldn't find 'TradeSkillMaster_AuctionDB.lua' in any of the following locations: {str(file_path_list)}. Check if TSM is installed and if so, run a full scan first.")

def upload_data():
    ret = None
    logger.debug("UPLOAD BLOCK")
    
    lua_file_paths, json_file = get_lua_file_paths()
    
    files_new = []
    files_updated = []
    for lua_file_path in lua_file_paths:
        obj = next((d for d in json_file["file_info"] if d["file_path"] == lua_file_path), None)
        if not obj:
            files_new.append(lua_file_path)
            continue
            
        if obj["last_modified"] != os.path.getmtime(lua_file_path):
            files_updated.append(obj)
    
    if files_new or files_updated:
        full_file_info = get_lua_file_path_info(lua_file_paths)
        
        if files_new:
            logger.info("Upload block - New LUA file(s) detected")
            file_info_new_files = [{"file_path": f["file_path"], "last_modified": f["last_modified"]} for f in full_file_info if f["file_path"] in files_new]
            json_file["file_info"].extend(file_info_new_files)
        
        if files_updated:
            logger.debug("Changes to LUA file(s) detected")
            json_file["file_info"] = [o for o in json_file["file_info"] if o not in files_updated]
            file_info_updated_files = [f for f in full_file_info if f["file_path"] in [f["file_path"] for f in files_updated]]
            json_file["file_info"].extend([{"file_path": f["file_path"], "last_modified": f["last_modified"]} for f in file_info_updated_files])
            
        latest_data = get_latest_scans_across_all_accounts_and_realms(full_file_info)
        
        updated_realms = []
        if json_file["latest_data"] != latest_data:
            for la in latest_data:
                if la["last_complete_scan"] > next((r["last_complete_scan"] for r in json_file["latest_data"] if r["realm"] == la["realm"]), 0):
                    updated_realms.append(la)
                    
        if updated_realms:
            dev_server_regex = r"(?i)\b(?:alpha|dev|development|ptr|qa|recording)\b"
            updated_realms_to_send = [r for r in updated_realms if not re_search(dev_server_regex, r["realm"])]
            if updated_realms_to_send:
                logger.info(f"""Upload block - New scan timestamp found for realms: {", ".join(["'" + r["realm"] + "'" for r in updated_realms_to_send])}""")
                for r in updated_realms_to_send:
                    r["username"] = hash_username(r["username"])

                data_to_send_json_string = json.dumps(updated_realms_to_send)
                data_to_send_bytes = io.BytesIO(data_to_send_json_string.encode('utf-8'))
                logger.debug("Sending data")
                import_result = send_data_to_server(data_to_send_bytes)
            
                if not import_result:
                    logger.info(f"Upload block - Upload failed. Will retry next round. ({current_tries['upload_tries']}/{HTTP_TRY_CAP})")
                    return ret
                
                logger.info("Upload block - " + import_result['message'])
                ret = import_result['update_count']
            else:
                logger.debug("New scan timestamp found but only for Dev/PTR/QA etc servers, ignoring")
            
            for r in updated_realms:
                json_file_obj = next((l for l in json_file["latest_data"] if l["realm"] == r["realm"]), None)
                if json_file_obj:
                    json_file_obj["last_complete_scan"] = r["last_complete_scan"]
                else:
                    json_file["latest_data"].append(r)
            
            write_json_file(json_file)
            interruptible_sleep(15) # allow for server-side file generation
        else:
            write_json_file(json_file)
            logger.debug("Upload block - Despite LUA file(s) being updated, there are no new scan timestamps")
    else:
        logger.debug("No changes detected in LUA file(s)")
        
    return ret

def is_ascension_running():
    logger.debug("Checking if Ascension is running")
    return 'Ascension.exe' in (p.name() for p in process_iter())

def get_lua_file_paths():
    json_file = read_json_file()
    wtf_folder = json_file["wtf_path"]
    lua_file_paths = get_tsm_auctiondb_lua_files(wtf_folder)
    
    return lua_file_paths, json_file

def redact_account_name_from_lua_file_path(lua_file_path):
    return re_sub(r"(?<=(?:\\|/)Account(?:\\|/))[^\\\/]+", "{REDACTED}", lua_file_path)

def get_account_name_from_lua_file_path(lua_file_path):
    match = re_search(r"(?<=(?:\\|/)Account(?:\\|/))[^\\\/]+", lua_file_path)
    if match:
        return match[0]
    return None

def download_data():
    ret = None
    logger.debug("DOWNLOAD BLOCK")
    if not is_ascension_running():
        downloaded_data = get_data_from_server()
        if not downloaded_data:
            logger.debug(f"Download failed. Will retry next round. ({current_tries['download_tries']}/{HTTP_TRY_CAP})")
            return ret
        lua_file_paths, json_file = get_lua_file_paths()
        
        need_to_update_json = False
        need_to_update_lua_file = False
        updated_realms = set()
        for lua_file_path in lua_file_paths:
            with open(lua_file_path, "r") as outfile:
                logger.debug(f"Processing '{redact_account_name_from_lua_file_path(lua_file_path)}'")
                data = luadata_serialization.unserialize(outfile.read(), encoding="utf-8", multival=False)
                for download_obj in downloaded_data:
                    logger.debug(f"""Processing '{download_obj["realm"]}'""")
                    if "realm" in data:
                        if not data["realm"] and isinstance(data["realm"], list):
                            logger.debug("data['realm'] is empty list")
                            data["realm"] = {}
                            
                        if download_obj["realm"] in data["realm"]:
                            if data["realm"][download_obj["realm"]]["lastCompleteScan"] < download_obj["last_complete_scan"]:
                                logger.debug(f"""'{download_obj["realm"]}' in data['realm'], updating it""")
                                data["realm"][download_obj["realm"]]["lastCompleteScan"] = download_obj["last_complete_scan"]
                                data["realm"][download_obj["realm"]]["scanData"] = download_obj["scan_data"]
                                need_to_update_lua_file = True
                                updated_realms.add(download_obj["realm"])
                            else:
                                logger.debug(f"""'{download_obj["realm"]}' data is up-to-date, no need to rewrite it""")
                                continue
                        else:
                            logger.debug(f"""'{download_obj["realm"]}' not in data['realm'], adding it""")
                            data["realm"][download_obj["realm"]] = {}
                            data["realm"][download_obj["realm"]]["lastCompleteScan"] = download_obj["last_complete_scan"]
                            data["realm"][download_obj["realm"]]["lastScanSecondsPerPage"] = 0.5
                            data["realm"][download_obj["realm"]]["scanData"] = download_obj["scan_data"]
                            need_to_update_lua_file = True
                            updated_realms.add(download_obj["realm"])
                    else:
                        logger.debug(f"""'realm' key not in data, adding it and setting up realm '{download_obj["realm"]}'""")
                        data["realm"] = {}
                        data["realm"][download_obj["realm"]] = {}
                        data["realm"][download_obj["realm"]]["lastCompleteScan"] = download_obj["last_complete_scan"]
                        data["realm"][download_obj["realm"]]["lastScanSecondsPerPage"] = 0.5
                        data["realm"][download_obj["realm"]]["scanData"] = download_obj["scan_data"]
                        need_to_update_lua_file = True
                        updated_realms.add(download_obj["realm"])
                
                if need_to_update_lua_file:
                    prefix = """-- Updated by Ascension TSM Data Sharing App (https://github.com/Seminko/Ascension-TSM-Data-Sharing-App)\nAscensionTSM_AuctionDB = """
                    luadata_serialization.write(lua_file_path, data, encoding="utf-8", indent="\t", prefix=prefix)
                    file_obj = next(f for f in json_file["file_info"] if f["file_path"] == lua_file_path)
                    file_obj["last_modified"] = os.path.getmtime(lua_file_path)
                    need_to_update_json = True
        
        if need_to_update_json:
            ret = True
            logger.info(f"""Download block - LUA file(s) updated with data for realms: '{", ".join(updated_realms)}'""")
            logger.debug("Json data needs to be updated")
            for download_obj in [d for d in downloaded_data if d["realm"] in updated_realms]:
                logger.debug(f"""Checking realm '{download_obj["realm"]}'""")
                realm_dict = next((realm for realm in json_file["latest_data"] if realm["realm"] == download_obj["realm"]), None)
                if realm_dict:
                    logger.debug(f"""Realm '{download_obj["realm"]}' in json data, updating it""")
                    realm_dict["last_complete_scan"] = download_obj["last_complete_scan"]
                    realm_dict["scan_data"] = download_obj["scan_data"]
                else:
                    logger.debug(f"""Realm '{download_obj["realm"]}' not in json data, adding it""")
                    download_obj["username"] = get_account_name_from_lua_file_path(lua_file_paths[0])
                    download_obj = {k: download_obj[k] for k in ["realm", "last_complete_scan", "username", "scan_data"]}
                    json_file["latest_data"].append(download_obj)
            write_json_file(json_file)
            logger.debug("json data updated")
        else:
            logger.debug("LUA file(s) are up-to-date for all realms")
            logger.debug("json data is up-to-date, no need to rewrite it")
    else:
        logger.debug("Ascension is running, skipping download")
    
    return ret

def clear_message(msg):
    sys.stdout.write('\r' + ' ' * len(msg) + '\r')
    sys.stdout.flush()
    
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
        
def app_start_logging():
    logger.info(f"{APP_NAME} started")
    logger.info(SEPARATOR)
    logger.info("Make sure you have Windows notifications enabled (check GitHub FAQ).")
    logger.info("DON'T BE A SCRUB, UPLOAD FREQUENTLY.")
    logger.info(SEPARATOR)

# %% MAIN LOOP

def main():
    global MAX_VERSION
    
    app_start_logging()
    MAX_VERSION = check_for_new_versions()
    
    if not json_file_initialized():
        initiliaze_json()
    
    remove_old_logs()
    
    last_upload_time = 0
    last_download_time = 0
    last_update_check = time.time()
    
    loading_chars = ["[   ]","[=  ]","[== ]","[===]","[ ==]","[  =]"]
    loading_char_idx = 0
    msg = ""
    old_msg = ""
    
    while True:
        current_time = time.time()
        
        if current_time - last_upload_time >= UPLOAD_INTERVAL_SECONDS:
            clear_message(msg)
            ret = upload_data()
            if ret or ret == 0: # ret in this context holds the number of updated items
                if ret:
                    write_to_upload_stats({'time': time.time(), 'version': VERSION, 'items_updated': ret})
                logger.info(SEPARATOR)
            else:
                logger.debug(SEPARATOR)
            last_upload_time = current_time
        
        if current_time - last_download_time >= DOWNLOAD_INTERVAL_SECONDS:
            clear_message(msg)
            ret = download_data()
            if ret:
                logger.info(SEPARATOR)
            else:
                logger.debug(SEPARATOR)
            last_download_time = current_time
        
        if current_time - last_update_check >= UPDATE_INTERVAL_SECONDS or MAX_VERSION == None:
            clear_message(msg)
            MAX_VERSION = check_for_new_versions()
            last_update_check = time.time()
            
        old_msg = msg
        msg = time.strftime("%Y-%m-%d %H:%M:%S,000") + " - " + loading_chars[loading_char_idx % len(loading_chars)] + " - Detecting changes (Next upload in " + str(round((UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time))/60, 1)) + "min / Next download in " + str(round((DOWNLOAD_INTERVAL_SECONDS - (current_time - last_download_time))/60,1)) + "min)"
        if len(old_msg) > len(msg):
            clear_message(old_msg)
        sys.stdout.write('\r' + msg)
        sys.stdout.flush()
        loading_char_idx += 1
        time.sleep(0.5)


if __name__ == "__main__":
    if "logger" not in globals() and "logger" not in locals():
        logger = get_logger()
        
    session = requests.Session()
    session.mount("https://", ADAPTER)
    session.mount("http://", ADAPTER)
        
    try:
        main()
    except Exception:
        if VERSION < MAX_VERSION:
            exception_msg = "An exception occurred, likely because you're not using the most recent version of this app. Before reporting, please download the latest release (EXE) here: 'https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/releases'. If that doesn't help, send the logs to Mortificator on Discord (https://discord.gg/uTxuDvuHcn --> Addons from Szyler and co --> #tsm-data-sharing - tag @Mortificator) or create an issue on Github (https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/issues)"
        else:
            exception_msg = "An exception occurred. Please send the logs to Mortificator on Discord (https://discord.gg/uTxuDvuHcn --> Addons from Szyler and co --> #tsm-data-sharing - tag @Mortificator) or create an issue on Github (https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/issues)"
        logger.critical(exception_msg)
        logger.exception("Exception")
        input("Press any key to close the console")