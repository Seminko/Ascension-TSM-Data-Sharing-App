# %% LOCAL IMPORTS

from logger_config import logger
from generic_helper import write_to_json, read_from_json, clear_message
from toast_notification import create_generic_notification
from server_communication import get_messages, current_tries
from config import HTTP_TRY_CAP, MESSAGES_FILE_PATH, SEPARATOR

# %% MODULE IMPORTS

import os
import json

# %% FUNCTIONS

"Max msg len to easily read = 237 chars"

def handle_messages(console_msg=""):
    messages_from_server = get_messages()
    if messages_from_server is None:
        logger.debug(f"Getting massaged failed. Will retry next round. ({current_tries['get_messages_tries']}/{HTTP_TRY_CAP})")
        return console_msg

    if not messages_from_server:
        logger.debug("There are no messages to display")
        return console_msg

    file_exists = os.path.exists(MESSAGES_FILE_PATH)
    if file_exists:
        processed_messages = json.loads(read_from_json(MESSAGES_FILE_PATH))
    else:
        processed_messages = []

    messages_to_process = [msg for msg in messages_from_server if msg["message_id"] not in [m["message_id"] for m in processed_messages]]
    if messages_to_process:
        console_msg = clear_message(console_msg)
        for idx, msg in enumerate(messages_to_process):
            create_generic_notification("For your information", msg["message"], urgent=False)
            logger.info(f'SERVER MESSAGE: {msg["message"]}')
            logger.info(SEPARATOR)
            processed_messages.append(msg)

        write_to_json(MESSAGES_FILE_PATH, processed_messages)

    return console_msg