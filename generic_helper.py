# %% LOCAL IMPORTS

from logger_config import logger
from config import SCRIPT_DIR, NUMBER_OF_LOGS_TO_KEEP, SEPARATOR, MAIN_SEPARATOR,\
    APP_NAME, UPLOAD_STATS_PATH, UPLOAD_STATS_ACHIEVEMENTS, UPLOAD_INTERVAL_SECONDS,\
    LOADING_CHARS, UPLOAD_LOOPS_PER_DOWNLOAD, VERSION, UPDATER_PATH, EXE_PATH,\
    GITHUB_REPO_URL, DISCORD_INVITE_LINK, UPDATE_PREFERENCES_PATH, UPDATE_PREFERENCES_FILE_NAME
from toast_notification import create_generic_notification

# %% MODULE IMPORTS

import os
import sys
import time
import json
from psutil import process_iter, NoSuchProcess, ZombieProcess
import subprocess

# %% FUNCTIONS

def app_start_logging():
    logger.info(MAIN_SEPARATOR)
    logger.info(f"{APP_NAME} started")
    logger.info(GITHUB_REPO_URL)
    logger.info(MAIN_SEPARATOR)
    logger.info("Make sure you have Windows notifications enabled (check GitHub FAQ).")
    logger.info("DON'T TOUCH 'update_times.json'! YOU'LL BREAK SOMETHING.")
    logger.info("DON'T BE A SCRUB, UPLOAD FREQUENTLY.")
    logger.info(SEPARATOR)

def update_preferences_string_to_bool(update_preferences):
    changed = False
    if update_preferences["update_automatically_without_prompting"] in ["True", "true", "y", "yes"]:
        update_preferences["update_automatically_without_prompting"] = True
        changed = True
    elif update_preferences["update_automatically_without_prompting"] in ["False", "false", "n", "no"]:
        update_preferences["update_automatically_without_prompting"] = False
        changed = True
    return changed, update_preferences

def clear_message(msg):
    sys.stdout.write('\r' + ' ' * len(msg) + '\r')
    sys.stdout.flush()
    return ""

def clear_message_and_write_new(old_msg, msg):
    clear_message(old_msg)
    msg = write_message(msg, append=False)
    return msg

def get_files(dst_folder):
    return [f for f in os.listdir(dst_folder) if os.path.isfile(os.path.join(dst_folder, f))]

def get_loading_msg(is_ascension_running_now, loading_char_idx, current_time, last_upload_time, current_upload_loop_count):
    first_part = LOADING_CHARS[loading_char_idx % len(LOADING_CHARS)] +\
                 " - Idling (Next upload in " +\
                 str(round(max((UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time))/60, 0), 1)) + " min "
    if not is_ascension_running_now:
        second_part = "/ Next download in " +\
                      str(round((seconds_until_next_trigger(current_upload_loop_count, UPLOAD_LOOPS_PER_DOWNLOAD) +\
                      (UPLOAD_INTERVAL_SECONDS - (current_time - last_upload_time))) / 60, 1)) + " min)"
    else:
        second_part = "/ Next download on Ascension close)"
    return first_part + second_part

def interruptible_sleep(seconds):
    start_time = time.time()
    end_time = start_time + seconds

    while time.time() < end_time:
        time.sleep(0.1)  # Sleep in smaller increments

def is_ascension_running():
    # logger.debug("Checking if Ascension is running")
    for p in process_iter(['name']):
        try:
            return any(
                p.info['name'].lower() == 'ascension.exe' 
                for p in process_iter(['name'])
            )
        except (NoSuchProcess, ZombieProcess):
            pass
    return False

def log_exception_message_and_quit(max_version):
    if max_version and VERSION < max_version:
        exception_msg = f"An exception occurred, likely because you're not using the most recent version of this app. Before reporting, please download the latest release (EXE) here: '{GITHUB_REPO_URL}/releases'. If that doesn't help, send the logs to Mortificator on Discord ({DISCORD_INVITE_LINK} --> Other DEVs Addons (N-Z) --> #tsm-data-sharing - tag @Mortificator) or create an issue on Github ({GITHUB_REPO_URL}/issues)"
    else:
        exception_msg = f"An exception occurred. Please send the logs to Mortificator on Discord ({DISCORD_INVITE_LINK} --> Other DEVs Addons (N-Z) --> #tsm-data-sharing - tag @Mortificator) or create an issue on Github ({GITHUB_REPO_URL}/issues)"

    logger.critical(exception_msg)
    logger.exception("Exception")

    input("Press Enter to close the console")

def prompt_yes_no(message):
    while True:
        logger.debug(f"{message} [Y/N]")
        response = input(f"{time.strftime('%Y-%m-%d %H:%M:%S,%MS')} - {message} [Y/N]: ").lower()
        logger.debug(f"User entered: '{response}'")
        if response in ["y", "yes", "ye", "ya", "ys", "yea", "yeh" "yeah"]:
            return True
        elif response in ["n", "no", "nope", "nah", "ne", "nein"]:
            return False

def get_update_preferences():
    update_preferences = None
    file_initialized_previously = os.path.exists(UPDATE_PREFERENCES_PATH)
    if not file_initialized_previously:
        logger.info("Auto-Updater has been implemented. These updates can either happen automatically")
        logger.info("(completely without your input) or only when you acknowledge the update prompt.")
        if prompt_yes_no("Would you like for the updates to happen automatically without prompting?"):
            update_preferences = {"update_automatically_without_prompting": True}
        else:
            update_preferences = {"update_automatically_without_prompting": False}
        write_to_json(UPDATE_PREFERENCES_PATH, update_preferences)
        logger.info(f"If you ever change your mind, delete '{UPDATE_PREFERENCES_FILE_NAME}' and it will trigger")
        logger.info("this setup again. Or, if you're brave, open the file and change the value to true / false.")

    if update_preferences is None:
        update_preferences_str = read_from_json(UPDATE_PREFERENCES_PATH)
        update_preferences = json.loads(update_preferences_str)

    logger.debug(f'update_automatically_without_prompting: {update_preferences["update_automatically_without_prompting"]}')
    if isinstance(update_preferences["update_automatically_without_prompting"], bool):
        if not file_initialized_previously:
            logger.info(SEPARATOR)
        return update_preferences["update_automatically_without_prompting"]
    elif isinstance(update_preferences["update_automatically_without_prompting"], str):
        changed, update_preferences = update_preferences_string_to_bool(update_preferences)
        if changed:
            write_to_json(UPDATE_PREFERENCES_PATH, update_preferences)
            if not file_initialized_previously:
                logger.info(SEPARATOR)
            return update_preferences["update_automatically_without_prompting"]
        logger.critical(f"It seems you changed '{UPDATE_PREFERENCES_FILE_NAME}'. The only allowed values are true / false.")

    raise ValueError('update_preferences["update_automatically_without_prompting"] is not a bool!')

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

def run_updater():
    logger.debug("Running updater")
    subprocess.Popen([UPDATER_PATH, str(os.getpid()), EXE_PATH], creationflags=subprocess.CREATE_NEW_CONSOLE)

def seconds_until_next_trigger(current_upload_loops_count, trigger_interval_loops):
    remainder = current_upload_loops_count % trigger_interval_loops
    if remainder == 0:
        return 0
    else:
        return (trigger_interval_loops - remainder) * UPLOAD_INTERVAL_SECONDS

def write_message(msg, append=False):
    msg_to_send = f'\r{time.strftime("%Y-%m-%d %H:%M:%S,000")} - {msg}' if not append else f", {msg}"
    sys.stdout.write(msg_to_send)
    sys.stdout.flush()
    return msg_to_send

def write_idling_message(old_msg, is_ascension_running_now, loading_char_idx, current_time, last_upload_time, current_upload_loop_count):
    msg = get_loading_msg(is_ascension_running_now, loading_char_idx, current_time, last_upload_time, current_upload_loop_count)
    if len(old_msg) > len(f'\r{time.strftime("%Y-%m-%d %H:%M:%S,000")} - {msg}'):
        clear_message(old_msg)
    msg = write_message(msg, append=False)
    return msg

def write_to_json(json_path, json_dict):
    with open(json_path, "w") as outfile:
        outfile.write(json.dumps(json_dict, indent=4))

def read_from_json(json_path):
    with open(json_path, "r") as file:
        return file.read()

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

                write_to_json(UPLOAD_STATS_PATH, upload_stats_json)

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

    write_to_json(UPLOAD_STATS_PATH, upload_stats_json)

    create_generic_notification("ACHIEVEMENT UNLOCKED!", f"Your first upload! Keep it up! Proud of you!&#10;So far you helped update {upload_stats_json['total_items_updated']:,} items.")
    logger.info(SEPARATOR)
    logger.info("ACHIEVEMENT UNLOCKED! Your first upload! Keep it up! Proud of you!")
    logger.info(f"So far you helped update {upload_stats_json['total_items_updated']:,} items.")