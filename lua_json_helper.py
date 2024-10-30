# %% LOCAL IMPORTS

from logger_config import logger
import luadata_serialization
from get_wtf_folder import get_wtf_folder
from hash_username import hash_username
from task_scheduler import create_task_from_xml
from config import SCRIPT_DIR, SEPARATOR, JSON_FILE_NAME,\
    EXE_PATH, XML_TASK_DEFINITION_PATH, JSON_PATH

# %% MODULE IMPORTS

import os
import sys
import re
import json

# %% FUNCTIONS

def get_account_name_from_lua_file_path(lua_file_path):
    match = re.search(r"(?<=(?:\\|/)Account(?:\\|/))[^\\\/]+", lua_file_path)
    if match:
        return match[0]
    return None

def get_all_account_names(json_file, hashed=True):
    file_paths = [f["file_path"] for f in json_file["file_info"]]
    account_names = [get_account_name_from_lua_file_path(f) for f in file_paths]
    if not hashed:
        return account_names
    hashed_account_names = [hash_username(an) for an in account_names]
    return hashed_account_names

def get_last_complete_scan(lua_file_path):
    logger.debug(f"Getting last complete scans for '{redact_account_name_from_lua_file_path(lua_file_path)}'")
    with open(lua_file_path, "r") as outfile:
        data = luadata_serialization.unserialize(outfile.read(), encoding="utf-8", multival=False)
        realm_list = []
        if "realm" in data:
            for realm in {k:v for k, v in data["realm"].items() if "scanData" in data["realm"][k]}:
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

def get_lua_file_paths():
    json_file = read_json_file()
    wtf_folder = json_file["wtf_path"]
    lua_file_paths = get_tsm_auctiondb_lua_files(wtf_folder)
    
    return lua_file_paths, json_file

def json_file_initialized():
    logger.debug("Checking if json file is initialized")
    if next((f for f in os.listdir() if f == JSON_FILE_NAME), None):
        return True
    return False

def get_latest_scans_across_all_accounts_and_realms(file_info):
    logger.debug("Getting latest scan ascross all accounts and realms")
    last_updates = [{"realm": r["realm"], "last_complete_scan": r["last_complete_scan"], "scan_data": r["scan_data"], "username": re.search(r"(?<=\\Account\\)([^\\]+)", f["file_path"])[0]} for f in file_info for r in f["realm_last_complete_scan"]]
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
        logger.critical(f"Couldn't find 'TradeSkillMaster_AuctionDB.lua' in any of the following locations: {str([redact_account_name_from_lua_file_path(f) for f in file_path_list])}. Check if TSM is installed and if so, run a full scan first.")
        input("Press any key to close the console")
        sys.exit()

def initiliaze_json():
    logger.info("It seems this is the first time using the app, here's what's going to happen:")
    logger.info("First you will be asked whether you want to create a startup task. This will make sure")
    logger.info("the app runs automatically when you turn on your PC and starts downloading latest data.")
    create_task_from_xml(task_name="TSM Data Sharing App", exe_path=EXE_PATH, working_directory=SCRIPT_DIR, xml_path=XML_TASK_DEFINITION_PATH)
    logger.info(SEPARATOR)
    logger.info(f"Initializing '{JSON_FILE_NAME}'")
    logger.info("Now the app will look for your WTF folder. If you installed Ascension in the default")
    logger.info("directory it will find it automatically. If not, you will be prompted to find it yourself.")
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
    logger.info(SEPARATOR)
    logger.info("Now you will be prompted to link your account(s) to a Discord User ID / Nickname")
    logger.info("After this the app will ONLY mention successful uploads / downloads")
    logger.info(SEPARATOR)

def read_json_file():
    logger.debug("Reading json file")
    with open(JSON_PATH, "r") as outfile:
        json_object = json.loads(outfile.read())
        return json_object

def redact_account_name_from_lua_file_path(lua_file_path):
    return re.sub(r"(?<=(?:\\|/)Account(?:\\|/))[^\\\/]+", "{REDACTED}", lua_file_path)

def write_json_file(json_object):
    logger.debug("Saving json file")
    with open(JSON_PATH, "w") as outfile:
        json_string = json.dumps(json_object, indent=4)
        outfile.write(json_string)