# %% LOCAL IMPORTS

from logger_config import logger
from config import SCRIPT_DIR, NUMBER_OF_LOGS_TO_KEEP, SEPARATOR, MAIN_SEPARATOR,\
    APP_NAME, UPLOAD_STATS_PATH, UPLOAD_STATS_ACHIEVEMENTS
from toast_notification import create_generic_notification


# %% MODULE IMPORTS

import os
import sys
import time
import json
from psutil import process_iter

# %% FUNCTIONS

def app_start_logging():
    logger.info(MAIN_SEPARATOR)
    logger.info(f"{APP_NAME} started")
    logger.info("https://github.com/Seminko/Ascension-TSM-Data-Sharing-App")
    logger.info(MAIN_SEPARATOR)
    logger.info("Make sure you have Windows notifications enabled (check GitHub FAQ).")
    logger.info("DON'T TOUCH 'update_times.json'! YOU'LL BREAK SOMETHING.")
    logger.info("DON'T BE A SCRUB, UPLOAD FREQUENTLY.")
    logger.info(SEPARATOR)

def clear_message(msg):
    sys.stdout.write('\r' + ' ' * len(msg) + '\r')
    sys.stdout.flush()

def get_files(dst_folder):
    return [f for f in os.listdir(dst_folder) if os.path.isfile(os.path.join(dst_folder, f))]

def interruptible_sleep(seconds):
    start_time = time.time()
    end_time = start_time + seconds
    
    while time.time() < end_time:
        time.sleep(0.1)  # Sleep in smaller increments

def is_ascension_running():
    logger.debug("Checking if Ascension is running")
    return 'Ascension.exe' in (p.name() for p in process_iter())

def log_exception_message_and_quit(max_version):
    if VERSION < max_version:
        exception_msg = "An exception occurred, likely because you're not using the most recent version of this app. Before reporting, please download the latest release (EXE) here: 'https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/releases'. If that doesn't help, send the logs to Mortificator on Discord (https://discord.gg/uTxuDvuHcn --> Addons from Szyler and co --> #tsm-data-sharing - tag @Mortificator) or create an issue on Github (https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/issues)"
    else:
        exception_msg = "An exception occurred. Please send the logs to Mortificator on Discord (https://discord.gg/uTxuDvuHcn --> Addons from Szyler and co --> #tsm-data-sharing - tag @Mortificator) or create an issue on Github (https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/issues)"
    
    logger.critical(exception_msg)
    logger.exception("Exception")
    
    input("Press any key to close the console")

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