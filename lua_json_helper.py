# %% LOCAL IMPORTS

from logger_config import logger
import luadata_serialization
from get_wtf_folder import get_wtf_folder
from hash_username import hash_username
from task_scheduler import create_task_from_xml
from generic_helper import write_to_json, clear_message
from config import SCRIPT_DIR, SEPARATOR, JSON_FILE_NAME,\
    EXE_PATH, XML_TASK_DEFINITION_PATH, JSON_PATH, APP_NAME_WITHOUT_VERSION

# %% MODULE IMPORTS

import os
import re
import json
import pathlib

# %% FUNCTIONS

def create_empty_auctiondb_lua_file(auctiondb_lua_file_path):
    logger.debug(f"No TradeSkillMaster_AuctionDB.lua file in {auctiondb_lua_file_path}, creating it")
    os.makedirs(auctiondb_lua_file_path, exist_ok=True)
    with open(os.path.join(auctiondb_lua_file_path, "TradeSkillMaster_AuctionDB.lua"), "w") as outfile:
        empty_db_str = 'AscensionTSM_AuctionDB = {\n	["profiles"] = {\n		'\
            '["Default"] = {\n			["lastGetAll"] = 0,\n		},\n	},\n}'
        outfile.write(empty_db_str)

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
        lua_content = outfile.read()
        if not validate_lua_db_is_acension(lua_content):
            logger.critical(f"'{lua_file_path}' was NOT created by the official Ascension TSM Addon hence skipping it. Download the official Ascension TSM addon from the launcher or from https://github.com/Ascension-Addons/TradeSkillMaster")
            return None, None
        data = luadata_serialization.unserialize(lua_content, encoding="utf-8", multival=False)
        realm_list = []
        if "realm" in data:
            for realm in {k:v for k, v in data["realm"].items() if "scanData" in data["realm"][k]}:
                obj = {}
                obj["realm"] = realm
                obj["last_complete_scan"] = data["realm"][realm]["lastCompleteScan"]
                obj["scan_data"] = data["realm"][realm]["scanData"]
                realm_list.append(obj)
        return realm_list, data

def get_lua_file_path_info(lua_file_paths):
    file_updated_list = []
    for lua_file_path in lua_file_paths:
        logger.debug(f"Getting lua file path info for '{redact_account_name_from_lua_file_path(lua_file_path)}'")
        obj = {}
        obj["file_path"] = lua_file_path
        obj["last_modified"] = os.path.getmtime(lua_file_path)
        realm_last_complete_scan, full_data = get_last_complete_scan(lua_file_path)
        if realm_last_complete_scan is None or full_data is None:
            continue
        obj["realm_last_complete_scan"] = realm_last_complete_scan
        obj["full_data"] = full_data
        file_updated_list.append(obj)
    return file_updated_list

def get_lua_file_paths(msg=""):
    json_file = read_json_file()
    wtf_folder = json_file["wtf_path"]
    
    """
    json_file["wtf_path"] was originally a string, changed to list in newer versions
    needs to be changed retroactively
    """
    if isinstance(wtf_folder, str):
        msg = clear_message(msg)
        json_file["wtf_path"] = [pathlib.Path(json_file["wtf_path"]).as_posix()]
        wtf_folder = get_wtf_folder(json_file["wtf_path"])
        json_file["wtf_path"] = list(set([pathlib.Path(p).as_posix() for p in wtf_folder]))
        
        "also fix all the other paths so they are consistent"
        unique_file_info = {}
        for item in json_file["file_info"]:
            posix_path = pathlib.Path(item['file_path']).as_posix()
            # Create a copy of the item with the POSIX path
            new_item = {**item, "file_path": posix_path}
            
            # Keep only the most recent last_modified
            if posix_path not in unique_file_info or new_item['last_modified'] > unique_file_info[posix_path]['last_modified']:
                unique_file_info[posix_path] = new_item
        
        unique_file_info_final = list(unique_file_info.values())
        json_file["file_info"] = unique_file_info_final
        
        write_json_file(json_file)
        wtf_folder = json_file["wtf_path"]
        
        logger.info(SEPARATOR)
        
    wtf_folder = set(wtf_folder)
    lua_file_paths = get_tsm_auctiondb_lua_files(wtf_folder)

    return lua_file_paths, json_file, msg

def json_file_initialized():
    logger.debug("Checking if json file is initialized")
    if next((f for f in os.listdir() if f == JSON_FILE_NAME), None):
        return True
    return False

def get_latest_scans_across_all_accounts_and_realms(file_info):
    logger.debug("Getting latest scan ascross all accounts and realms")
    last_updates = [{"realm": r["realm"], "last_complete_scan": r["last_complete_scan"], "scan_data": r["scan_data"], "username": re.search(r"(?<=(?:\\|/)Account(?:\\|/))[^\\\/]+", f["file_path"])[0]} for f in file_info for r in f["realm_last_complete_scan"]]
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

def get_latest_scans_per_realm_from_json_file():
    json_file = read_json_file()
    return {dct["realm"]: dct["last_complete_scan"] for dct in json_file["latest_data"]}

def get_tsm_auctiondb_lua_files(wtf_folder):
    logger.debug("Getting all lua files for all accounts")
    "Gets 'TradeSkillMaster_AuctionDB.lua' file paths for all accounts"
    account_names = [{"wtf": w, "account_name": a} for w in wtf_folder for a in os.listdir(os.path.join(w, "Account")) if os.path.isdir(os.path.join(w, "Account", a))]

    found_file_path_list = []
    for account_name in account_names:
        saved_var_path = os.path.join(account_name["wtf"],
                                     "Account",
                                     account_name["account_name"],
                                     "SavedVariables")
        path = os.path.join(saved_var_path, "TradeSkillMaster_AuctionDB.lua")
        if not os.path.isfile(path):
            create_empty_auctiondb_lua_file(saved_var_path)
        found_file_path_list.append(pathlib.Path(path).as_posix())

    return found_file_path_list

def initiliaze_json():
    logger.info("It seems this is the first time using the app, here's what's going to happen:")
    logger.info("First you will be asked whether you want to create a startup task. This will make sure")
    logger.info("the app runs automatically when you turn on your PC and starts downloading latest data.")
    create_task_from_xml(task_name=APP_NAME_WITHOUT_VERSION, exe_path=EXE_PATH, working_directory=SCRIPT_DIR, xml_path=XML_TASK_DEFINITION_PATH)
    logger.info(SEPARATOR)
    logger.info(f"Initializing '{JSON_FILE_NAME}'")
    logger.info("Now the app will look for your WTF folder. If you installed Ascension in the default")
    logger.info("directory it will find it automatically. If not, you will be prompted to find it yourself.")
    wtf_folder = list(get_wtf_folder())
    lua_file_paths = get_tsm_auctiondb_lua_files(wtf_folder)
    file_info = get_lua_file_path_info(lua_file_paths)
    if not file_info:
        raise ValueError("TSM DB LUA file was NOT created by the official Ascension TSM Addon. Download the official Ascension TSM addon from the launcher or from https://github.com/Ascension-Addons/TradeSkillMaster")
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

def validate_lua_db_is_acension(lua_content):
    regex = r"^(?:--\s*.*\s*)*\s*AscensionTSM_AuctionDB\s*=\s*{"
    match = re.search(regex, lua_content)
    if match:
        return True
    return False

def write_json_file(json_object):
    logger.debug("Saving json file")
    write_to_json(JSON_PATH, json_object)