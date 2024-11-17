# %% LOCAL IMPORTS

from config import NICKNAME_FILE_NAME_PATH, SEPARATOR, GITHUB_REPO_URL
from logger_config import logger
import lua_json_helper
from hash_username import hash_username
from server_communication import set_user
from toast_notification import create_generic_notification
from generic_helper import prompt_yes_no, write_to_json

# %% MODULE IMPORTS

import time
import json
from json import JSONDecodeError
import os

# %% FUNCTIONS

def check_discord_id_nickname(notification=False):
    logger.debug("Checking Discord User ID")
    json_file = lua_json_helper.read_json_file()
    if not os.path.exists(NICKNAME_FILE_NAME_PATH):
        logger.debug("Username not set up yet")
        discord_id_nickname_full_process(json_file)
        return
    else:
        logger.debug("Username set up already")
        if json_file.get("username_last_modified") != os.path.getmtime(NICKNAME_FILE_NAME_PATH):
            logger.debug("Discord User ID / Nickname file modified")
            discord_id_nickname_str = get_discord_id_nickname_from_file()
            if not discord_id_nickname_str:
                logger.info("Discord User ID / Nickname file is empty. Please set it up again")
                discord_id_nickname_full_process(json_file)
                return
            else:
                discord_id_nickname_dict = parse_discord_id_nickname_str_to_dict(discord_id_nickname_str)
                if discord_id_nickname_dict is None:
                    logger.info("Discord User ID / Nickname file cannot be parsed. Please set it up again")
                    discord_id_nickname_full_process(json_file)
                    return
                    
                if json_file.get("username_last_value") == discord_id_nickname_dict and is_account_list_unchanged(json_file):
                    logger.debug("Despite the file being modified content didn't change and no new accounts added")
                    set_discord_id_nickname_to_main_json_file(json_file, discord_id_nickname_dict)
                    return
        elif is_account_list_unchanged(json_file):
            logger.debug("Discord User ID / Nickname file remains unchanged")
            return
        else:
            logger.debug("Account list changed")
            discord_id_nickname_str = get_discord_id_nickname_from_file()
            discord_id_nickname_dict = parse_discord_id_nickname_str_to_dict(discord_id_nickname_str)
            
            if discord_id_nickname_dict is None:
                logger.info("Discord User ID / Nickname file cannot be parsed. Please set it up again")
                discord_id_nickname_full_process(json_file)
                return
                
            if json_file.get("username_last_value") == discord_id_nickname_dict and is_account_list_unchanged(json_file):
                logger.debug("Despite the file being modified content didn't change and no new accounts added")
                set_discord_id_nickname_to_main_json_file(json_file, discord_id_nickname_dict)
                return
    
    
    if json_file.get("username_last_value") != discord_id_nickname_dict:
        logger.info("Discord User ID / Nickname file content changed. Revalidating")
    accounts_failed_validation = [account_name for account_name in discord_id_nickname_dict.keys() if not validate_both_values(discord_id_nickname_dict[account_name]["discord_user_id"], discord_id_nickname_dict[account_name]["nickname"])]
    newly_added_accounts = get_newly_added_accounts(json_file)
    if accounts_failed_validation or newly_added_accounts:
        if notification:
            create_generic_notification("Attention required!", "Changes detected to your account(s) / Discord User ID / Nickname.\nThe app is now paused and is waiting for your input.")
        if accounts_failed_validation:
            logger.info(f"""These accounts failed validation: '{"','".join(accounts_failed_validation)}'.""")
        if newly_added_accounts:
            logger.info(f"""These accounts were added since last time they got checked: '{"','".join(newly_added_accounts)}'.""")
        logger.info("Let's set them up.")
        discord_id_nickname_dict = set_up_specific_accounts(accounts_failed_validation+newly_added_accounts, discord_id_nickname_dict)
    discord_id_nickname_full_process(json_file, discord_id_nickname_dict)        
    
def change_discord_id_nickname_psa():
    logger.info("---")
    logger.info("If you ever want to change your Discord User ID and / or nickname,")
    logger.info("you can update it in 'discord_id_username.json'.")

def discord_id_nickname_full_process(json_file, discord_id_nickname_dict=None):
    if discord_id_nickname_dict is None:
        unhased_account_names = lua_json_helper.get_all_account_names(json_file, hashed=False)
        discord_id_nickname_dict = get_user_id_initial(unhased_account_names)
    "Some might add discord user id as int, which makes sense, so I don't want to bother them with revalidation."
    "The values are being converted to string during validation and finally set as strings before saving the values."
    discord_id_nickname_dict = {k: {key: str(val) if val is not None and val != "" else None for key, val in v.items()} for k, v in discord_id_nickname_dict.items()}
    write_to_json(NICKNAME_FILE_NAME_PATH, discord_id_nickname_dict)
    set_discord_id_nickname_to_main_json_file(json_file, discord_id_nickname_dict)
    discord_id_nickname_send_to_server(discord_id_nickname_dict)
    logger.info(SEPARATOR)

def discord_id_nickname_send_to_server(discord_id_nickname_dict):
    "HASH USERNAME BEFORE SENDING"
    discord_user_id_nickname_to_send = {hash_username(k):v for k, v in discord_id_nickname_dict.items()}
    import_result = set_user(discord_user_id_nickname_to_send)
    logger.info(f"Server response: {import_result['message']}")

def get_discord_id_nickname_from_file():
    with open(NICKNAME_FILE_NAME_PATH, "r") as outfile:
        discord_id_nickname_str = outfile.read()
    return discord_id_nickname_str

def get_newly_added_accounts(json_file):
    if "username_last_value" in json_file:
        return list(set(lua_json_helper.get_all_account_names(json_file, hashed=False)) - set(json_file["username_last_value"].keys()))
    return lua_json_helper.get_all_account_names(json_file, hashed=False)

def get_user_id_initial(unhashed_account_names, ):
    while True:
        logger.info("For stats / leaderboards let's link the account name(s) to a nickname you go by")
        logger.info("Optional: give your Discord User ID, if you want to be tagged when posting stats.")
        if not prompt_yes_no("Would you like to participate?"):
            logger.info("Setting '<no username>' as your nickname.")
            change_discord_id_nickname_psa()
            return {uan: {"discord_user_id": None, "nickname": "<no username>"} for uan in unhashed_account_names}
        
        if len(unhashed_account_names) == 1:
            logger.info("---")
            discord_user_id_nickname_dict = get_user_id_input()
            change_discord_id_nickname_psa()
            return {unhashed_account_names[0]: discord_user_id_nickname_dict}
        
        logger.info("---")
        logger.info(f"There are {len(unhashed_account_names)} accounts:")
        logger.info(f"""'{"','".join(sorted(unhashed_account_names))}'""")
        if prompt_yes_no("Are all of them yours?"):
            discord_user_id_nickname_dict = get_user_id_input()
            change_discord_id_nickname_psa()
            return {uan: discord_user_id_nickname_dict for uan in unhashed_account_names}
        
        logger.info("---")
        logger.info("Let's set up all the accounts, even the ones that are not yours.")
        logger.info("Don't set Discord User ID for accounts which are not yours. (If you're not sure.)")
        logger.info("Use nickname placeholder for accounts which are not yours. (If you're not sure.)")
        account_name_discord_user_id_nickname_dict = {}
        for unhashed_account_name in unhashed_account_names:
            logger.info("---")
            logger.info(f"Setting up account '{unhashed_account_name}'")
            account_name_discord_user_id_nickname_dict[unhashed_account_name] = get_user_id_input()
        change_discord_id_nickname_psa()
        return account_name_discord_user_id_nickname_dict

def get_user_id_input():
    discord_id = None
    logger.info("Discord User ID is a 18-19 digit number (unique identifier). To get it, you have to enable")
    logger.info("Developer mode in the discord app (cogwheel-advanced-developer mode), then right click")
    logger.info("your name and select Copy User ID. If you're not sure how to enable Developer mode,")
    logger.info(f"check Github readme ({GITHUB_REPO_URL}).")
    if prompt_yes_no("Would you like to input your Discord User ID?"):
        discord_id = prompt_for_discord_id()
    if discord_id:
        logger.info("Since you gave your Discord ID, it would be great if the nickname matched")
        logger.info("your Discord username.")
    nickname_result = prompt_for_nickname()

    return {"discord_user_id": discord_id, "nickname": nickname_result}

def is_account_list_unchanged(json_file):
    if "username_last_value" in json_file:
        return set(lua_json_helper.get_all_account_names(json_file, hashed=False)) == set(json_file["username_last_value"].keys())
    return True

def parse_discord_id_nickname_str_to_dict(discord_id_nickname_str):
    try:
        discord_id_nickname_dict = json.loads(discord_id_nickname_str)
    except JSONDecodeError:
        discord_id_nickname_dict = None
    finally:
        return discord_id_nickname_dict

def prompt_for_discord_id():
    while True:
        logger.info("---")
        logger.debug("Paste your Discord User ID here: ")
        discord_id = input(f"{time.strftime('%Y-%m-%d %H:%M:%S,%MS')} - Paste your Discord User ID here: ")
        logger.debug(f"User entered: '{discord_id}'")
        if validate_discord_user_id(discord_id):
            return discord_id
        else:
            logger.info("Invalid Discord User ID. Please try again.")

def prompt_for_nickname():
    while True:
        logger.info("---")
        logger.debug("Enter your nickname here: ")
        nickname = input(f"{time.strftime('%Y-%m-%d %H:%M:%S,%MS')} - Enter your nickname here: ")
        logger.debug(f"User entered: '{nickname}'")
        if validate_nickname(nickname):
            return nickname
        else:
            logger.info("Invalid nickname. Please try again.")
    
def set_discord_id_nickname_to_main_json_file(json_file, discord_id_nickname_dict):
    json_file["username_last_modified"] = os.path.getmtime(NICKNAME_FILE_NAME_PATH)
    json_file["username_last_value"] = discord_id_nickname_dict
    lua_json_helper.write_json_file(json_file)
    
def set_up_specific_accounts(accounts_to_be_set_up, discord_id_nickname_dict):
    for account in accounts_to_be_set_up:
        logger.info(f"Setting up account '{account}'")
        discord_id_nickname_dict[account] = get_user_id_input()
        logger.info("---")
    return discord_id_nickname_dict

def validate_both_values(discord_user_id, nickname):
    return validate_discord_user_id(discord_user_id) and validate_nickname(nickname)

def validate_discord_user_id(discord_user_id):
    if discord_user_id == "":
        logger.debug("Discord User ID is empty string. Changing it to None")
        discord_user_id = None
    if discord_user_id is None:
        logger.debug("Discord User ID validated")
        return True
    if not isinstance(discord_user_id, str):
        discord_user_id = str(discord_user_id)
    if not discord_user_id.isnumeric():
        logger.critical(f"Discord User ID '{discord_user_id}' is not numeric. It is supposed to be a 18-19 digit number.")
        return False
    if len(discord_user_id) not in [18, 19]:
        logger.critical(f"Discord User ID '{discord_user_id}' is not of appropriate length. It is supposed to be a 18-19 digit number.")
        return False
    logger.debug("Discord User ID validated")
    return True

def validate_nickname(nickname):
    if nickname is None:
        logger.critical("You put 'null' as the nickname value in the json file you snake!")
        return False
    if not isinstance(nickname, str):
        nickname = str(nickname)
    if len(nickname) < 2:
        logger.critical(f"Nicknames must be at least 2 characters long. '{nickname}' is not.")
        return False
    if len(nickname) > 32:
        logger.critical(f"Nicknames cannot be longer than 32 characters. '{nickname}' is.")
        return False
    if nickname.strip().lower() == "everyone" or nickname.strip().lower() == "here":
        logger.critical("Nicknames cannot be 'everyone' or 'here'.")
        return False
    if [char for char in ["@", "#", ":", "```", "discord"] if char in nickname]:
        logger.critical(f"Nicknames cannot contain the following: '@', '#', ':', '```', 'discord'. '{nickname}' does.")
        return False
    logger.debug("Nickname validated")
    return True