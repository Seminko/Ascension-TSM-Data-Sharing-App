from get_wtf_folder import get_wtf_folder
from save_shortcut import create_shortcut_to_startup
from hash_username import hash_username
from get_endpoints import get_upload_endpoint, get_download_endpoint
import luadata_serialization

from os import path as os_path, listdir as os_listdir, makedirs as os_makedirs, remove as os_remove
from json import dumps as json_dumps, loads as json_loads
from json.decoder import JSONDecodeError
from time import time as time_time, sleep as time_sleep, strftime as time_strftime
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from re import sub as re_sub, search as re_search
from psutil import process_iter
import sys

import io
import json

VERSION = 0.9

JSON_FILE_NAME = "update_times.json"
#SCRIPT_DIR = os_path.dirname(os_path.abspath(__file__))
if getattr(sys, 'frozen', False):
    # Running in PyInstaller executable
    SCRIPT_DIR = os_path.dirname(sys.executable)
else:
    # Running as a regular Python script
    SCRIPT_DIR = os_path.dirname(os_path.abspath(__file__))
JSON_PATH = os_path.join(SCRIPT_DIR, JSON_FILE_NAME)

UPLOAD_INTERVAL_SECONDS = 300
DOWNLOAD_INTERVAL_SECONDS = 3600
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

session = requests.Session()
session.mount("https://", ADAPTER)
session.mount("http://", ADAPTER)

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

def send_data_to_server(data_to_send):
    logger.debug("Sending data to server")
    global session
    url = get_upload_endpoint()
    # response = session.post(url, json=data_to_send, timeout=REQUEST_TIMEOUT)
    try:
        response = session.post(url, data=generate_chunks(data_to_send), timeout=REQUEST_TIMEOUT, stream=True)
        if response.status_code == 400:
            logger.critical(f"Sending to DB failed: '{process_response_text(response.text)}'")
        elif response.status_code != 200:
            logger.critical(f"Sending to DB failed. Status code: {response.status_code}")
        response.raise_for_status()
    except Exception as e:
        logger.critical(f"Sending to DB failed even after {MAX_RETRIES} tries")
        raise e
    
    response_json = response.json()
    
    return response_json

def get_data_from_server():
    logger.debug("Downloading data from server")
    global session
    url = get_download_endpoint()
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 400:
            logger.critical(f"Downloading from DB failed: '{process_response_text(response.text)}'")
        elif response.status_code != 200:
            logger.critical(f"Downloading from DB failed. Status code: {response.status_code}")
        response.raise_for_status()
    except Exception as e:
        logger.critical(f"Downloading from DB failed even after {MAX_RETRIES} tries")
        raise e
        
    response_list = response.text.split("||")
    return int(response_list[0]), response_list[1]
    
def interruptible_sleep(seconds):
    start_time = time_time()
    end_time = start_time + seconds
    
    while time_time() < end_time:
        time_sleep(0.1)  # Sleep in smaller increments

def get_files(dst_folder):
    return [f for f in os_listdir(dst_folder) if os_path.isfile(os_path.join(dst_folder, f))]

def remove_old_logs():
    logger.debug("Checking for old logs to be removed")
    dst_folder = os_path.join(SCRIPT_DIR, 'logs')
    file_list = get_files(dst_folder)
    if len(file_list) > NUMBER_OF_LOGS_TO_KEEP:
        full_path_list = [dst_folder + "\\" + i for i in file_list]
        full_path_list.sort()
        logs_to_remove = full_path_list[NUMBER_OF_LOGS_TO_KEEP:]
        word = "logs"
        if len(logs_to_remove) == 1:
            word = "log"
        logger.info(f"Removing {len(logs_to_remove)} oldest {word}") 
        for log_to_remove in logs_to_remove:
            try:
                os_remove(log_to_remove)
            except PermissionError as e:
                logger.debug(f"Removing log '{log_to_remove}' failed due to: '{str(repr(e))}'") 
    else:
        logger.debug("No logs to be removed")

def get_logger():
    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # Set the overall log level to DEBUG
    
    # Console handler with INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Time Rotating File handler with DEBUG level
    log_dir = os_path.join(SCRIPT_DIR, 'logs')
    if not os_path.exists(log_dir):
        os_makedirs(log_dir)
    log_file = os_path.join(log_dir, 'ascension_tsm_data_sharing_app')
    
    timestamp = time_strftime("%Y%m%d_%H%M%S")
    log_file_with_suffix = f"{log_file}_v{VERSION}_{timestamp}"

    file_handler = logging.FileHandler(f"{log_file_with_suffix}.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - [%(funcName)s]: %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def json_file_initialized():
    logger.debug("Checking if json file is initialized")
    if next((f for f in os_listdir() if f == JSON_FILE_NAME), None):
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
    startup_folder = create_shortcut_to_startup()
    logger.info(f"Startup shortcut created: '{startup_folder}'")
    
    logger.info(f"Initializing '{JSON_FILE_NAME}'")
    wtf_folder = get_wtf_folder()
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
        
def write_json_file(json_object):
    logger.debug("Saving json file")
    with open(JSON_PATH, "w") as outfile:
        json_string = json_dumps(json_object, indent=4)
        outfile.write(json_string)
        
def read_json_file():
    logger.debug("Reading json file")
    with open(JSON_PATH, "r") as outfile:
        json_object = json_loads(outfile.read())
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
        obj["last_modified"] = os_path.getmtime(lua_file_path)
        obj["realm_last_complete_scan"] = get_last_complete_scan(lua_file_path)
        file_updated_list.append(obj)
    return file_updated_list

def get_tsm_auctiondb_lua_files(wtf_folder):
    logger.debug("Getting all lua files for all accounts")
    "Gets 'TradeSkillMaster_AuctionDB.lua' file paths for all accounts"
    account_names = os_listdir(os_path.join(wtf_folder, "Account"))
    
    found_file_path_list = []
    file_path_list = []
    for account_name in account_names:
        path = os_path.join(wtf_folder,
                            "Account",
                            account_name,
                            "SavedVariables",
                            "TradeSkillMaster_AuctionDB.lua")
        file_path_list.append(path)
        if os_path.isfile(path):
            found_file_path_list.append(path)
            
    if found_file_path_list:
        return found_file_path_list
    else:
        raise ValueError(f"Couldn't find 'TradeSkillMaster_AuctionDB.lua' in any of the following locations: {str(file_path_list)}. Check if TSM is installed and if so, run a full scan first.")

def upload_data():
    logger.info("UPLOAD BLOCK")
    
    lua_file_paths, json_file = get_lua_file_paths()
    
    files_new = []
    files_updated = []
    for lua_file_path in lua_file_paths:
        obj = next((d for d in json_file["file_info"] if d["file_path"] == lua_file_path), None)
        if not obj:
            files_new.append(lua_file_path)
            continue
            
        if obj["last_modified"] != os_path.getmtime(lua_file_path):
            files_updated.append(obj)
    
    if files_new or files_updated:
        full_file_info = get_lua_file_path_info(lua_file_paths)
        
        if files_new:
            logger.info("Upload block - New LUA file(s) detected")
            file_info_new_files = [f for f in full_file_info if f["file_path"] in [f["file_path"] for f in files_new]]
            json_file["file_info"].extend(file_info_new_files)
        
        if files_updated:
            logger.info("Upload block - Changes to LUA file(s) detected")
            json_file["file_info"] = [o for o in json_file["file_info"] if o not in files_updated]
            file_info_updated_files = [f for f in full_file_info if f["file_path"] in [f["file_path"] for f in files_updated]]
            json_file["file_info"].extend([{"file_path": f["file_path"], "last_modified": f["last_modified"]} for f in file_info_updated_files])
            
        latest_data = get_latest_scans_across_all_accounts_and_realms(full_file_info)
        
        realms_to_be_pushed = []
        if json_file["latest_data"] != latest_data:
            for la in latest_data:
                if la["last_complete_scan"] > next((r["last_complete_scan"] for r in json_file["latest_data"] if r["realm"] == la["realm"]), 0):
                    realms_to_be_pushed.append(la)
                    
        if [r for r in realms_to_be_pushed if r["realm"] == 'Area 52 - Free-Pick']:
            logger.info("Upload block - New scan timestamp found")
            
            "WE WILL NEED ONE DB TABLE FOR EACH REALM, for now Area52 only"
            area_52_only_import_data = next(r for r in realms_to_be_pushed if r["realm"] == 'Area 52 - Free-Pick')
            
            data_to_send = {"scan_data": area_52_only_import_data["scan_data"], "username": hash_username(area_52_only_import_data["username"])}
            
            "-----------------------------------------------------------------------------------"
            "FOR DATA STREAMING"
            data_to_send_json_string = json.dumps(data_to_send)
            data_to_send_bytes = io.BytesIO(data_to_send_json_string.encode('utf-8'))
            import_result = send_data_to_server(data_to_send_bytes)
            "-----------------------------------------------------------------------------------"
            
            # import_result = send_data_to_server(data_to_send)
            logger.info("Upload block - " + import_result['message'])
            
            for r in realms_to_be_pushed:
                json_file_obj = next((l for l in json_file["latest_data"] if l["realm"] == r["realm"]), None)
                if json_file_obj:
                    json_file_obj["last_complete_scan"] = r["last_complete_scan"]
                else:
                    json_file["latest_data"].append(r)
            
            write_json_file(json_file)
            interruptible_sleep(15) # allow for server-side file generation
        else:
            write_json_file(json_file)
            logger.info("Upload block - Despite LUA file(s) being updated, there are no new scan timestamps")
    else:
        logger.info("Upload block - No changes detected in LUA file(s)")


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

def download_data():
    logger.info("DOWNLOAD BLOCK")
    if not is_ascension_running():
        last_complete_scan, scan_data = get_data_from_server()
        lua_file_paths, json_file = get_lua_file_paths()
        
        need_to_update_json = False
        for lua_file_path in lua_file_paths:
            with open(lua_file_path, "r") as outfile:
                logger.debug(f"Download block - processing '{redact_account_name_from_lua_file_path(lua_file_path)}'")
                data = luadata_serialization.unserialize(outfile.read(), encoding="utf-8", multival=False)
                if "realm" in data:
                    if not data["realm"] and isinstance(data["realm"], list):
                        logger.debug("Donwload block, data['realm'] is empty list")
                        data["realm"] = {}
                        
                    if "Area 52 - Free-Pick" in data["realm"]:
                        if data["realm"]["Area 52 - Free-Pick"]["lastCompleteScan"] < last_complete_scan:
                            logger.debug("Donwload block, 'Area 52 - Free-Pick' in data['realm']")
                            data["realm"]["Area 52 - Free-Pick"]["lastCompleteScan"] = last_complete_scan
                            data["realm"]["Area 52 - Free-Pick"]["scanData"] = scan_data
                        else:
                            logger.debug("Donwload block, 'Area 52 - Free-Pick' data is up-to-date, no need to rewrite it")
                            continue
                    else:
                        logger.debug("Donwload block, 'Area 52 - Free-Pick' not in data['realm']")
                        data["realm"]["Area 52 - Free-Pick"] = {}
                        data["realm"]["Area 52 - Free-Pick"]["lastCompleteScan"] = last_complete_scan
                        data["realm"]["Area 52 - Free-Pick"]["lastScanSecondsPerPage"] = 0.5
                        data["realm"]["Area 52 - Free-Pick"]["scanData"] = scan_data
                else:
                    logger.debug("Donwload block, realm not in data")
                    data["realm"] = {}
                    data["realm"]["Area 52 - Free-Pick"] = {}
                    data["realm"]["Area 52 - Free-Pick"]["lastCompleteScan"] = last_complete_scan
                    data["realm"]["Area 52 - Free-Pick"]["lastScanSecondsPerPage"] = 0.5
                    data["realm"]["Area 52 - Free-Pick"]["scanData"] = scan_data
                
                prefix = """-- Updated by Ascension TSM Data Sharing App (https://github.com/Seminko/Ascension-TSM-Data-Sharing-App)\nAscensionTSM_AuctionDB = """
                luadata_serialization.write(lua_file_path, data, encoding="utf-8", indent="\t", prefix=prefix)
                file_obj = next(f for f in json_file["file_info"] if f["file_path"] == lua_file_path)
                file_obj["last_modified"] = os_path.getmtime(lua_file_path)
                need_to_update_json = True
        
        if need_to_update_json:
            realm_dict = next((realm for realm in json_file["latest_data"] if realm["realm"] == "Area 52 - Free-Pick"), None)
            if realm_dict:
                realm_dict["last_complete_scan"] = last_complete_scan
                realm_dict["scan_data"] = scan_data
            write_json_file(json_file)
            logger.info("Download block - Completed. All LUA files updated successfully.")
        else:
            logger.info("Donwload block, 'Area 52 - Free-Pick' json data is up-to-date, no need to rewrite it")
    else:
        logger.info("Download block - Ascension is running, skipping download")
    

if "logger" not in globals() and "logger" not in locals():
    logger = get_logger()

    
def main():
    if not json_file_initialized():
        initiliaze_json()
    
    remove_old_logs()
    
    last_upload_time = 0
    last_download_time = 0
    while True:
        current_time = time_time()
        
        if current_time - last_upload_time >= UPLOAD_INTERVAL_SECONDS:
            upload_data()
            last_upload_time = current_time
            
        if current_time - last_download_time >= DOWNLOAD_INTERVAL_SECONDS:
            download_data()
            last_download_time = current_time

        interruptible_sleep(5)
        
if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("An exception occurred")
        input("An exception occured (see above). Pres any key to close the console")