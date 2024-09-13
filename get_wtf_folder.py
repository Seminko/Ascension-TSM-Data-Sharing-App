from os import path as os_path, walk as os_walk
from platform import system
from select_dir import select_folder

def get_possible_paths():
    """
    Get a list of possible paths where Ascension WoW might be installed based on the OS.

    :return: A list of paths to search.
    """
    os_type = system()
    possible_paths = []

    if os_type != "Windows":
        raise Exception("The app is only available for Windows")

    drives = [f"{chr(x)}:\\" for x in range(65, 91) if os_path.exists(f"{chr(x)}:\\")]
    for drive in drives:
        # Add default known locations
        possible_paths.append(os_path.join(drive, "Program Files", "Ascension Launcher", "resources", "client"))
        possible_paths.append(os_path.join(drive, "Program Files (x86)", "Ascension Launcher", "resources", "client"))
        possible_paths.append(os_path.join(drive, "Games", "Ascension Launcher", "resources", "client"))
        possible_paths.append(os_path.join(drive, "Ascension Launcher", "resources", "client"))
    # # LINUX IS UNTESTED
    # elif os_type == "Linux":
    #     home_dir = os_path.expanduser("~")
    #     # Add default known locations
    #     possible_paths.append(os_path.join(home_dir, ".ascension", "client"))
    #     possible_paths.append(os_path.join(home_dir, "Games", "Ascension Launcher", "resources", "client"))
    #     possible_paths.append(os_path.join(home_dir, "Ascension", "resources", "client"))
    #     possible_paths.append(os_path.join("/", "opt", "Ascension Launcher", "resources", "client"))
    #     possible_paths.append(os_path.join("/", "usr", "local", "Ascension Launcher", "resources", "client"))

    return possible_paths

def find_wtf_folder(starting_paths, target_folder_name="WTF"):
    """
    Search for the WTF folder within the specified starting paths.

    :param starting_paths: List of paths where the search should begin.
    :param target_folder_name: The name of the folder to search for.
    :return: The full path to the WTF folder if found, otherwise None.
    """
    for starting_path in starting_paths:
        for root, dirs, files in os_walk(starting_path):
            if target_folder_name in dirs:
                return os_path.join(root, target_folder_name)

    return None

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
    
    folder_selected_path = select_folder()
    if not folder_selected_path.endswith(r"/WTF"):
        raise ValueError("Selected wrong folder. You must select the 'WTF' folder in Ascension directory.")
        
    return folder_selected_path


# get_wtf_folder()