from get_wtf_folder import get_wtf_folder
from save_shortcut import create_shortcut_to_startup

from datetime import datetime
from os import path as os_path, listdir as os_listdir
from luadata import unserialize as luadata_unserialize
from json import dumps as json_dumps, loads as json_loads
from json.decoder import JSONDecodeError
from time import time as time_time, sleep as time_sleep
import logging
import argparse
from requests import post as request_post
from re import sub as re_sub, search as re_search
import traceback

JSON_FILE_NAME = "update_times.json"
DETECT_CHANGES_INTERVAL_SECONDS = 300



"do some testing on this..."
def send_data_to_server(data_to_send):
    url =***REMOVED***
    cap = 5
    expn = None
    for rnd in range(1, cap+1):
        try:
            response = request_post(url, json=data_to_send)
        except Exception as e:
            expn = e
            logger.debug(f"Sending to db failed: {str(repr(e))}")
            interruptible_sleep(5)
            continue
        
        if response.status_code != 200:
            try:
                response_json = response.json()
            except (JSONDecodeError, ValueError):
                response_json = {"response text": re_sub("(?:\n+|\s\s+)", " ", re_sub('(?:<style>.*<\/style>|<[^<]+?>)', '', response.text)).strip()}
            logger.debug(f"Sending to db failed: {response_json}")
            interruptible_sleep(5)
            continue
        
        return response.json()
    if expn:
        raise expn
    raise Exception(f"Sending to db failed: {response_json}")

        
def interruptible_sleep(seconds):
    start_time = time_time()
    end_time = start_time + seconds
    
    while time_time() < end_time:
        time_sleep(0.1)  # Sleep in smaller increments
        
def parse_arguments():
    parser = argparse.ArgumentParser(description="A script with a debug option.")
    parser.add_argument(
        "--debug",
        action="store_true",  # This means the flag is optional and sets debug to True if present
        help="Enable debug mode"
    )

    return parser.parse_args()
        
def get_logger(debug):
    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # Set the overall log level to DEBUG
    
    # Console handler with INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Console logs only INFO and above
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    if debug:
        # File handler with DEBUG level
        file_handler = logging.FileHandler(f'ascension_tsm_{datetime.strftime(datetime.now(), "%Y%m%d%H%M%S")}.log')
        file_handler.setLevel(logging.DEBUG)  # File logs all levels
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def json_file_initialized():
    if next((f for f in os_listdir() if f == JSON_FILE_NAME), None):
        return True
    return False

def get_latest_scans_across_all_accounts_and_realms(file_info):
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
    
    obj = {}
    obj["wtf_path"] = wtf_folder
    obj["file_info"] = [{"file_path": f["file_path"], "last_modified": f["last_modified"]} for f in file_info]
    obj["latest_data"] = latest_data
    write_json_file(obj)
        
def write_json_file(json_object):
    with open(JSON_FILE_NAME, "w") as outfile:
        json_string = json_dumps(json_object, indent=4)
        outfile.write(json_string)
        
def read_json_file():
    with open(JSON_FILE_NAME, "r") as outfile:
        json_object = json_loads(outfile.read())
        return json_object
    
def get_last_complete_scan(lua_file_path):
    with open(lua_file_path, "r") as outfile:
        data = luadata_unserialize(outfile.read(), encoding="utf-8", multival=False)
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
        obj = {}
        obj["file_path"] = lua_file_path
        obj["last_modified"] = os_path.getmtime(lua_file_path)
        obj["realm_last_complete_scan"] = get_last_complete_scan(lua_file_path)
        file_updated_list.append(obj)
    return file_updated_list

def get_tsm_auctiondb_lua_files(wtf_folder):
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

args = parse_arguments()
debug = args.debug

if "logger" not in globals() and "logger" not in locals():
    logger = get_logger(debug)
    
def main():
    if not json_file_initialized():
        initiliaze_json()
        
    json_changed = True
    while True:
        if json_changed:
            json_file = read_json_file()
            wtf_folder = json_file["wtf_path"]
            lua_file_paths = get_tsm_auctiondb_lua_files(wtf_folder)
        
        missing_files = []
        files_updated = []
        for lua_file_path in lua_file_paths:
            obj = next((d for d in json_file["file_info"] if d["file_path"] == lua_file_path), None)
            if not obj:
                missing_files.append(lua_file_path)
                continue
                
            if obj["last_modified"] != os_path.getmtime(lua_file_path):
                files_updated.append(obj)
        
        if missing_files or files_updated:
            json_changed = True
            
            if missing_files:
                logger.info("New file detected")
                file_info = get_lua_file_path_info(missing_files)
                json_file["file_info"].extend(file_info)
            
            if files_updated:
                logger.info("Changes detected")
                json_file["file_info"] = [o for o in json_file["file_info"] if o not in files_updated]
                file_info = get_lua_file_path_info([f["file_path"] for f in files_updated])
                json_file["file_info"].extend([{"file_path": f["file_path"], "last_modified": f["last_modified"]} for f in file_info])
                
            file_info = get_lua_file_path_info(lua_file_paths)
            latest_data = get_latest_scans_across_all_accounts_and_realms(file_info)
            
            realms_to_be_pushed = []
            if json_file["latest_data"] != latest_data:
                for la in latest_data:
                    if la["last_complete_scan"] > next(r["last_complete_scan"] for r in json_file["latest_data"] if r["realm"] == la["realm"]):
                        realms_to_be_pushed.append(la)
                        
            if realms_to_be_pushed:
                logger.info("  New scan timestamp found")
                
                "WE WILL NEED ONE DB TABLE FOR EACH REALM, for now Area52 only"
                area_52_only_import_data = next(r for r in realms_to_be_pushed if r["realm"] == 'Area 52 - Free-Pick')
                
                data_to_send = {"scan_data": area_52_only_import_data["scan_data"], "username": area_52_only_import_data["username"]}
                import_result = send_data_to_server(data_to_send)
                logger.info("  " + import_result['message'])
                
                for r in realms_to_be_pushed:
                    json_file_obj = next((l for l in json_file["latest_data"] if l["realm"] == r["realm"]), None)
                    if json_file_obj:
                        json_file_obj["last_complete_scan"] = r["last_complete_scan"]
                    else:
                        json_file["latest_data"].append(r)
            else:
                logger.info("  Despite files being updated, no new scan time found")
            
            write_json_file(json_file)
        else:
            json_changed = False
            logger.info("No changes detected")
            
        interruptible_sleep(DETECT_CHANGES_INTERVAL_SECONDS)
        
if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("An exception occured (see above). Pres any key to close the console")