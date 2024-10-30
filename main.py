# %% LOCAL IMPORTS

from logger_config import logger
from get_discord_user_id import check_discord_id_nickname
import lua_json_helper
import server_communication
import luadata_serialization
from hash_username import hash_username
import generic_helper

# %% MODULE IMPORTS

import os
import json
import time
import re
import io
import sys

# %% GLOBAL VARS
max_version = None
from config import VERSION, UPLOAD_INTERVAL_SECONDS, HTTP_TRY_CAP, \
    DOWNLOAD_INTERVAL_SECONDS, UPDATE_INTERVAL_SECONDS, SEPARATOR,\
    DISCORD_ID_NICKNAME_INTERVAL_SECONDS, LOADING_CHARS
from server_communication import current_tries

# %% FUNCTIONS

def upload_data():
    ret = None
    logger.debug("UPLOAD SECTION")
    
    lua_file_paths, json_file = lua_json_helper.get_lua_file_paths()
    
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
        full_file_info = lua_json_helper.get_lua_file_path_info(lua_file_paths)
        
        if files_new:
            logger.info("UPLOAD SECTION - New LUA file(s) detected (probably a newly added account)")
            file_info_new_files = [{"file_path": f["file_path"], "last_modified": f["last_modified"]} for f in full_file_info if f["file_path"] in files_new]
            json_file["file_info"].extend(file_info_new_files)
        
        if files_updated:
            logger.debug("Changes to LUA file(s) detected")
            json_file["file_info"] = [o for o in json_file["file_info"] if o not in files_updated]
            file_info_updated_files = [f for f in full_file_info if f["file_path"] in [f["file_path"] for f in files_updated]]
            json_file["file_info"].extend([{"file_path": f["file_path"], "last_modified": f["last_modified"]} for f in file_info_updated_files])
            
        latest_data = lua_json_helper.get_latest_scans_across_all_accounts_and_realms(full_file_info)
        
        updated_realms = []
        if json_file["latest_data"] != latest_data:
            for la in latest_data:
                if la["last_complete_scan"] > next((r["last_complete_scan"] for r in json_file["latest_data"] if r["realm"] == la["realm"]), 0):
                    updated_realms.append(la)
                    
        if updated_realms:
            dev_server_regex = r"(?i)\b(?:alpha|dev|development|ptr|qa|recording)\b"
            updated_realms_to_send = [r for r in updated_realms if not re.search(dev_server_regex, r["realm"])]
            if updated_realms_to_send:
                logger.info("UPLOAD SECTION - New scan timestamp found for the following realms:")
                logger.info(f"""'{"','".join(sorted([r['realm'] for r in updated_realms_to_send]))}'""")
                for r in updated_realms_to_send:
                    r["username"] = hash_username(r["username"])

                data_to_send_json_string = json.dumps(updated_realms_to_send)
                data_to_send_bytes = io.BytesIO(data_to_send_json_string.encode('utf-8'))
                logger.debug("Sending data")
                import_result = server_communication.send_data_to_server(data_to_send_bytes)
            
                if not import_result:
                    logger.info(f"UPLOAD SECTION - Upload failed. Will retry next round. ({current_tries['upload_tries']}/{HTTP_TRY_CAP})")
                    return ret
                
                logger.info("UPLOAD SECTION - " + import_result['message'])
                ret = import_result['update_count']
            else:
                logger.debug("New scan timestamp found but only for Dev/PTR/QA etc servers, ignoring")
            
            for r in updated_realms:
                json_file_obj = next((l for l in json_file["latest_data"] if l["realm"] == r["realm"]), None)
                if json_file_obj:
                    json_file_obj["last_complete_scan"] = r["last_complete_scan"]
                else:
                    json_file["latest_data"].append(r)
            
            lua_json_helper.write_json_file(json_file)
            generic_helper.interruptible_sleep(15) # allow for server-side file generation
        else:
            lua_json_helper.write_json_file(json_file)
            logger.debug("Despite LUA file(s) being updated, there are no new scan timestamps")
    else:
        logger.debug("No changes detected in LUA file(s)")
        
    return ret

def download_data():
    ret = None
    logger.debug("DOWNLOAD SECTION")
    if not generic_helper.is_ascension_running():
        downloaded_data = server_communication.get_data_from_server()
        if not downloaded_data:
            logger.debug(f"Download failed. Will retry next round. ({current_tries['download_tries']}/{HTTP_TRY_CAP})")
            return ret
        lua_file_paths, json_file = lua_json_helper.get_lua_file_paths()
        
        need_to_update_json = False
        need_to_update_lua_file = False
        updated_realms = set()
        for lua_file_path in lua_file_paths:
            with open(lua_file_path, "r") as outfile:
                logger.debug(f"Processing '{lua_json_helper.redact_account_name_from_lua_file_path(lua_file_path)}'")
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
        
        hashed_account_names = lua_json_helper.get_all_account_names(json_file)
        if need_to_update_json:
            ret = True
            
            import_result = server_communication.set_download_stats({"hashed_account_names": hashed_account_names, "file_updated": True})
            if not import_result:
                logger.debug(f"Sending download stats failed. Will retry next round. ({current_tries['set_download_stats_tries']}/{HTTP_TRY_CAP})")
            logger.debug(f"Download stats: {import_result['message']}")
            
            logger.info("DOWNLOAD SECTION - LUA file(s) updated with data for the following realms:")
            logger.info(f"""'{"','".join(sorted(updated_realms))}'""")
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
                    download_obj["username"] = lua_json_helper.get_account_name_from_lua_file_path(lua_file_paths[0])
                    download_obj = {k: download_obj[k] for k in ["realm", "last_complete_scan", "username", "scan_data"]}
                    json_file["latest_data"].append(download_obj)
            lua_json_helper.write_json_file(json_file)
            logger.debug("json data updated")
        else:
            import_result = server_communication.set_download_stats({"hashed_account_names": hashed_account_names, "file_updated": False})
            if not import_result:
                logger.debug(f"Sending download stats failed. Will retry next round. ({current_tries['set_download_stats_tries']}/{HTTP_TRY_CAP})")
            logger.debug(f"Download stats: {import_result['message']}")
            logger.debug("LUA file(s) are up-to-date for all realms")
            logger.debug("json data is up-to-date, no need to rewrite it")
    else:
        logger.debug("Ascension is running, skipping download")
    
    return ret


# %% MAIN LOOP

def main():
    global max_version
    
    generic_helper.app_start_logging()
    max_version = server_communication.check_for_new_versions()
    
    if not lua_json_helper.json_file_initialized():
        lua_json_helper.initiliaze_json()
    
    check_discord_id_nickname()
    
    generic_helper.remove_old_logs()
    
    last_upload_time = 0
    last_download_time = 0
    last_update_check = time.time()
    last_discord_id_nickname_check = time.time()
    
    loading_char_idx = 0
    msg = ""
    old_msg = ""
    
    while True:
        current_time = time.time()
        
        if current_time - last_upload_time >= UPLOAD_INTERVAL_SECONDS:
            generic_helper.clear_message(msg)
            ret = upload_data()
            if ret or ret == 0: # ret in this context holds the number of updated items
                if ret:
                    generic_helper.write_to_upload_stats({'time': current_time , 'version': VERSION, 'items_updated': ret})
                logger.info(SEPARATOR)
            else:
                logger.debug(SEPARATOR)
            last_upload_time = current_time
        
        # pokud jede ascension, tak čekej, až se vypne, pak hned downloadni, pak čekej 15 min klasicky
        if current_time - last_download_time >= DOWNLOAD_INTERVAL_SECONDS:
            generic_helper.clear_message(msg)
            ret = download_data()
            if ret:
                logger.info(SEPARATOR)
            else:
                logger.debug(SEPARATOR)
            last_download_time = current_time
        
        if current_time - last_update_check >= UPDATE_INTERVAL_SECONDS or max_version == None:
            generic_helper.clear_message(msg)
            max_version = server_communication.check_for_new_versions()
            last_update_check = current_time
            
        if current_time - last_discord_id_nickname_check >= DISCORD_ID_NICKNAME_INTERVAL_SECONDS:
            generic_helper.clear_message(msg)
            check_discord_id_nickname(notification=True)
            last_discord_id_nickname_check = current_time
            
        if UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time) > DOWNLOAD_INTERVAL_SECONDS - (current_time - last_download_time) :
            logger.debug(f"updating last_download_time from {last_download_time}")
            last_download_time += ((UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time)) - (DOWNLOAD_INTERVAL_SECONDS - (current_time - last_download_time)))
            logger.debug(f"updating last_download_time to {last_download_time}")
        if UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time) > UPDATE_INTERVAL_SECONDS - (current_time - last_update_check):
            logger.debug(f"updating last_update_check from {last_update_check}")
            last_update_check += ((UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time)) - (UPDATE_INTERVAL_SECONDS - (current_time - last_update_check)))
            logger.debug(f"updating last_update_check to {last_update_check}")
        if UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time) > DISCORD_ID_NICKNAME_INTERVAL_SECONDS - (current_time - last_discord_id_nickname_check):
            logger.debug(f"updating last_discord_id_nickname_check from {last_discord_id_nickname_check}")
            last_discord_id_nickname_check += ((UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time)) - (DISCORD_ID_NICKNAME_INTERVAL_SECONDS - (current_time - last_discord_id_nickname_check)))
            logger.debug(f"updating last_discord_id_nickname_check to {last_discord_id_nickname_check}")

        old_msg = msg
        msg = time.strftime("%Y-%m-%d %H:%M:%S,000") + " - " + LOADING_CHARS[loading_char_idx % len(LOADING_CHARS)] + " - Idling (Next upload in " + str(round(max((UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time))/60, 0), 1)) + "min / Next download in " + str(round(max((DOWNLOAD_INTERVAL_SECONDS - (current_time - last_download_time)) / 60, 0), 1)) + "min)"
 
        if len(old_msg) > len(msg):
            generic_helper.clear_message(old_msg)
        sys.stdout.write('\r' + msg)
        sys.stdout.flush()
        loading_char_idx += 1
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        generic_helper.log_exception_message_and_quit(max_version)