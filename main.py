# %% LOCAL IMPORTS

from logger_config import logger
from get_discord_user_id import check_discord_id_nickname
import lua_json_helper
import server_communication
import luadata_serialization
from hash_username import hash_username
import generic_helper
from config import GITHUB_REPO_URL, APP_NAME
from toast_notification import create_generic_notification
from task_scheduler import re_set_startup_task
from messages import handle_messages

# %% MODULE IMPORTS

import os
import json
import time
import io
import copy

# %% GLOBAL VARS
max_version = None
from config import VERSION, HTTP_TRY_CAP, UPLOAD_LOOPS_PER_DOWNLOAD,\
    UPLOAD_LOOPS_PER_UPDATE, UPLOAD_LOOPS_PER_DISCORD_ID_NICKNAME,\
    UPLOAD_LOOPS_PER_GET_MESSAGES, UPLOAD_INTERVAL_SECONDS, SEPARATOR
from server_communication import current_tries
msg = ""

# %% FUNCTIONS

def upload_data():
    global msg
    ret = None
    full_file_info = None
    logger.debug("UPLOAD SECTION")

    lua_file_paths, json_file, msg = lua_json_helper.get_lua_file_paths(msg)

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
            msg = generic_helper.clear_message(msg)
            logger.info("UPLOAD SECTION - New LUA file(s) detected (probably a newly added account or added PTR etc.)")
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
                "+1 used to counteract -1 as per below"
                if la["last_complete_scan"] > (next((r["last_complete_scan"] for r in json_file["latest_data"] if r["realm"] == la["realm"]), 0)+1):
                    updated_realms.append(la)

        if updated_realms:
            updated_realms_to_send = [copy.deepcopy(r) for r in updated_realms]
            updated_realms_to_send.sort(key=lambda x: x["realm"])
            msg = generic_helper.clear_message(msg)
            logger.info("UPLOAD SECTION - New scan timestamp found for the following realms:")
            for r in updated_realms_to_send:
                logger.info(f"""'{r['realm']}'""")
                r["username"] = hash_username(r["username"])

            data_to_send_json_string = json.dumps(updated_realms_to_send)
            data_to_send_bytes = io.BytesIO(data_to_send_json_string.encode('utf-8'))
            logger.debug("Sending data")
            import_result = server_communication.send_data_to_server(data_to_send_bytes)

            if not import_result:
                logger.info(f"UPLOAD SECTION - Upload failed. Will retry next round. ({current_tries['upload_tries']}/{HTTP_TRY_CAP})")
                return ret, full_file_info

            logger.info("UPLOAD SECTION - " + import_result['message'])
            ret = import_result['update_count']

            """"
            -1 used to redownload anyways
            what can happen is that your data is a year old and you scan
            a single item, the lastCompleteScan will still show now() time and
            since the lastCompleteScan is new, it won't download anything from server
            this will ensure that a redownload happens (only if the uploaded
            changes are processed server-side), potentially updating other items as well locally
            """
            for r in updated_realms:
                json_file_obj = next((l for l in json_file["latest_data"] if l["realm"] == r["realm"]), None)
                if json_file_obj:
                    json_file_obj["last_complete_scan"] = r["last_complete_scan"] - 1
                else:
                    r["last_complete_scan"] -= 1
                    json_file["latest_data"].append(r)

            lua_json_helper.write_json_file(json_file)
            generic_helper.interruptible_sleep(15) # allow for server-side file generation
        else:
            lua_json_helper.write_json_file(json_file)
            logger.debug("Despite LUA file(s) being updated, there are no new scan timestamps")
    else:
        logger.debug("No changes detected in LUA file(s)")

    return ret, full_file_info

def download_data(full_file_info):
    global msg
    ret = None
    logger.debug("DOWNLOAD SECTION")
    if not generic_helper.is_ascension_running():
        latest_scans_per_realm = lua_json_helper.get_latest_scans_per_realm_from_json_file()
        logger.debug(f"Latest local scan times: {latest_scans_per_realm}")
        downloaded_data = server_communication.get_data_from_server(latest_scans_per_realm)
        if downloaded_data is None:
            logger.debug(f"Download failed. Will retry next round. ({current_tries['download_tries']}/{HTTP_TRY_CAP})")
            return ret
        if len(downloaded_data) == 0:
            logger.debug("LUA file(s) are up-to-date for all realms")
            return ret

        ret = True
        downloaded_data.sort(key=lambda x: x["realm"])
        logger.debug(f"""Downloaded newer data for the following realms: '{"','".join([realm["realm"] for realm in downloaded_data])}'""")
        json_file = lua_json_helper.read_json_file()

        "When a realm is not downloaded, process it still so that it propagates to other accounts (only if the last scan has been within the last 7 days)"
        realms_not_downloaded = [realm for realm in json_file["latest_data"] if realm["realm"] not in [realm["realm"] for realm in downloaded_data] and realm["last_complete_scan"] >= (time.time() - 604800)]
        logger.debug(f"""Adding the following realms from local previous scans so to potentially propagate to other accounts: '{"','".join([realm["realm"] for realm in realms_not_downloaded])}'""")
        json_file, lua_file_paths, full_file_info = update_lua_files(full_file_info, downloaded_data+realms_not_downloaded)

        hashed_account_names = lua_json_helper.get_all_account_names(json_file)

        import_result = server_communication.set_download_stats({"hashed_account_names": hashed_account_names, "file_updated": True})
        if not import_result:
            logger.debug(f"Sending download stats failed. Will retry next round. ({current_tries['set_download_stats_tries']}/{HTTP_TRY_CAP})")
        logger.debug(f"Download stats: {import_result['message']}")

        msg = generic_helper.clear_message(msg)
        logger.info("DOWNLOAD SECTION - LUA file(s) updated with data for the following realms:")
        for realm in downloaded_data:
            logger.info(f"""'{realm["realm"]}'""")
        logger.debug("Json data needs to be updated")
        for download_obj in downloaded_data:
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
        logger.debug("Ascension is running, skipping download")

    return ret

def update_lua_files(full_file_info, downloaded_data):
    lua_file_paths, json_file, _ = lua_json_helper.get_lua_file_paths()
    if not full_file_info:
        full_file_info = lua_json_helper.get_lua_file_path_info(lua_file_paths)
    for lua_file_path in lua_file_paths:
        need_to_update_lua_file = False
        data = next(f["full_data"] for f in full_file_info if f["file_path"] == lua_file_path)
        logger.debug(f"Processing '{lua_json_helper.redact_account_name_from_lua_file_path(lua_file_path)}'")
        for download_obj in downloaded_data:
            logger.debug(f"""Processing '{download_obj["realm"]}'""")
            if "realm" in data:
                if not data["realm"] and isinstance(data["realm"], list):
                    logger.debug("data['realm'] is empty list")
                    data["realm"] = {}

                if download_obj["realm"] in data["realm"]:
                    if data["realm"][download_obj["realm"]]["lastCompleteScan"] <= download_obj["last_complete_scan"]:
                        logger.debug(f"""'{download_obj["realm"]}' in data['realm'], updating it""")
                        data["realm"][download_obj["realm"]]["lastCompleteScan"] = download_obj["last_complete_scan"]
                        data["realm"][download_obj["realm"]]["scanData"] = download_obj["scan_data"]
                        need_to_update_lua_file = True
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
            else:
                logger.debug(f"""'realm' key not in data, adding it and setting up realm '{download_obj["realm"]}'""")
                data["realm"] = {}
                data["realm"][download_obj["realm"]] = {}
                data["realm"][download_obj["realm"]]["lastCompleteScan"] = download_obj["last_complete_scan"]
                data["realm"][download_obj["realm"]]["lastScanSecondsPerPage"] = 0.5
                data["realm"][download_obj["realm"]]["scanData"] = download_obj["scan_data"]
                need_to_update_lua_file = True

        if need_to_update_lua_file:
            prefix = f"""-- Updated by {APP_NAME} ({GITHUB_REPO_URL})\nAscensionTSM_AuctionDB = """
            luadata_serialization.write(lua_file_path, data, encoding="utf-8", indent="\t", prefix=prefix)
            file_obj = next(f for f in json_file["file_info"] if f["file_path"] == lua_file_path)
            file_obj["last_modified"] = os.path.getmtime(lua_file_path)

    return json_file, lua_file_paths, full_file_info

# %% MAIN LOOP

def main():
    global max_version

    """
    global msg since other functions will rewrite using sys.stdout.write
    need to keep msg len so that it can be cleared
    """
    global msg

    current_upload_loop_count = 0
    last_upload_time = 0
    loading_char_idx = 0

    generic_helper.app_start_logging()
    max_version, _ = server_communication.check_for_new_versions()

    handle_messages()

    if not lua_json_helper.json_file_initialized():
        lua_json_helper.initiliaze_json()

    check_discord_id_nickname()
    has_ascension_been_running = generic_helper.is_ascension_running()
    generic_helper.remove_old_logs()

    """
    Deleting old task, since the name has changed from 'TSM Data Sharing App'
    to the app name 'Ascension TSM Data Sharing App'
    """
    re_set_startup_task()

    """
    Note to self: Spyder displays sys.stdout.write incorrectly, creating spaces
    wehere there shouldn't be any. However, when compiled it prints fine.
    """
    while True:
        current_time = time.time()

        is_ascension_running_now = generic_helper.is_ascension_running()
        if not has_ascension_been_running and is_ascension_running_now:
            has_ascension_been_running = True

        "UPLOAD"            
        if (has_ascension_been_running and not is_ascension_running_now) or current_time - last_upload_time >= UPLOAD_INTERVAL_SECONDS:
            msg = generic_helper.clear_message_and_write_new(msg, "Checking upload")
            time.sleep(0.5)
            ret, full_file_info = upload_data()
            if ret or ret == 0: # ret in this context holds the number of updated items
                if ret:
                    generic_helper.write_to_upload_stats({'time': current_time , 'version': VERSION, 'items_updated': ret})
                logger.info(SEPARATOR)
            else:
                logger.debug(SEPARATOR)
            last_upload_time = current_time

            "DOWNLOAD"
            if not is_ascension_running_now and (has_ascension_been_running or generic_helper.seconds_until_next_trigger(current_upload_loop_count, UPLOAD_LOOPS_PER_DOWNLOAD) == 0):
                msg += generic_helper.write_message("Checking download", append=True if msg else False)
                time.sleep(0.5)
                ret = download_data(full_file_info)
                if ret:
                    logger.info(SEPARATOR)
                else:
                    logger.debug(SEPARATOR)

            "UPDATE"
            if (current_upload_loop_count != 0 and generic_helper.seconds_until_next_trigger(current_upload_loop_count, UPLOAD_LOOPS_PER_UPDATE) == 0) or max_version == None:
                msg += generic_helper.write_message("Checking new releases", append=True if msg else False)
                time.sleep(0.5)
                max_version, msg = server_communication.check_for_new_versions()

            "MESSAGES"
            if (current_upload_loop_count != 0 and generic_helper.seconds_until_next_trigger(current_upload_loop_count, UPLOAD_LOOPS_PER_GET_MESSAGES) == 0):
                msg += generic_helper.write_message("Getting messages", append=True if msg else False)
                time.sleep(0.5)
                msg = handle_messages(msg)

            "DISCORD ID / NICKNAME CHECK"
            if current_upload_loop_count != 0 and generic_helper.seconds_until_next_trigger(current_upload_loop_count, UPLOAD_LOOPS_PER_DISCORD_ID_NICKNAME) == 0:
                msg += generic_helper.write_message("Checking nickname changes", append=True if msg else False)
                time.sleep(0.5)
                msg = check_discord_id_nickname(notification=True, console_msg=msg)

            if has_ascension_been_running and not is_ascension_running_now:
                has_ascension_been_running = False

            current_upload_loop_count += 1

        msg = generic_helper.write_idling_message(msg, is_ascension_running_now, loading_char_idx, current_time, last_upload_time, current_upload_loop_count)

        loading_char_idx += 1
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        create_generic_notification("Exception!", "An exception occured. Report it pls!", urgent=True)
        generic_helper.clear_message(msg)
        # check max version because it could have changed since first running the script
        max_version_temp = server_communication.get_latest_version()
        if max_version_temp:
            max_version = max_version_temp
        generic_helper.log_exception_message_and_quit(max_version)