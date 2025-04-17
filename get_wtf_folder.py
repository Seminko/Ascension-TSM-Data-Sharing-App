# %% LOCAL IMPORTS

from logger_config import logger
from select_dir import select_folder

# %% MODULE  IMPORTS

import os
from platform import system
import asyncio

# %% FUNCTIONS

def get_possible_paths():
    """
    Get a list of possible paths where Ascension WoW might be installed based on the OS.

    :return: A list of paths to search.
    """
    os.type = system()
    possible_paths = []

    if os.type != "Windows":
        raise Exception("The app is only available for Windows")

    drives = [f"{chr(x)}:\\" for x in range(65, 91) if os.path.exists(f"{chr(x)}:\\")]
    for drive in drives:
        # Add default known locations
        possible_paths.append(os.path.join(drive, "Program Files", "Ascension Launcher", "resources", "client", "WTF", "Account"))
        possible_paths.append(os.path.join(drive, "Program Files (x86)", "Ascension Launcher", "resources", "client", "WTF", "Account"))
        possible_paths.append(os.path.join(drive, "Games", "Ascension Launcher", "resources", "client", "WTF", "Account"))
        possible_paths.append(os.path.join(drive, "Ascension Launcher", "resources", "client", "WTF", "Account"))
    # # LINUX IS UNTESTED
    # elif os.type == "Linux":
    #     home_dir = os.path.expanduser("~")
    #     # Add default known locations
    #     possible_paths.append(os.path.join(home_dir, ".ascension", "client"))
    #     possible_paths.append(os.path.join(home_dir, "Games", "Ascension Launcher", "resources", "client"))
    #     possible_paths.append(os.path.join(home_dir, "Ascension", "resources", "client"))
    #     possible_paths.append(os.path.join("/", "opt", "Ascension Launcher", "resources", "client"))
    #     possible_paths.append(os.path.join("/", "usr", "local", "Ascension Launcher", "resources", "client"))

    return possible_paths

def get_wtf_folder():
    """
    Run the WTF folder search with user input for custom paths.
    """
    # Get the possible paths based on OS
    starting_paths = get_possible_paths()

    # Search for the WTF folder
    wtf_folder = find_wtf_folder(starting_paths)

    if wtf_folder:
        return wtf_folder

    while True:
        logger.info("Couldn't find WTF folder automatically. Select it yourself.")
        logger.info("MAKE SURE the WTF folder contains Account sub-directory. If not, it is not the correct folder!")
        folder_selected_path = asyncio.run(select_folder())
        if folder_selected_path.endswith(r"/WTF"):
            if os.path.isdir(os.path.join(folder_selected_path, "Account")):
                break
            else:
                logger.warn("There is no Account sub-directory in the WTF folder you selected. Find the correct one and try again")
        else:
            logger.warn("Selected wrong folder. You must select the 'WTF' folder in Ascension directory. Try again")

    return folder_selected_path

def find_wtf_folder(starting_paths, target_folder_name="WTF"):
    """
    Search for the WTF folder within the specified starting paths.

    :param starting_paths: List of paths where the search should begin.
    :param target_folder_name: The name of the folder to search for.
    :return: The full path to the WTF folder if found, otherwise None.
    """
    for starting_path in starting_paths:
        if os.path.isdir(starting_path):
            "Does ./.. from Account back to WTF folder"
            return os.path.dirname(starting_path)

    return None