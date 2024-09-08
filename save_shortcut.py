from os import path as os_path, getenv as os_getenv
from  win32com.client import Dispatch
from sys import executable as sys_executable

def create_shortcut_to_startup():
    executable_path = sys_executable
    shortcut_name = 'AscensionTSM'
    
    # Define the path to the Startup folder
    startup_folder = os_path.join(os_getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    
    # Define the path for the shortcut
    shortcut_path = os_path.join(startup_folder, f"{shortcut_name}.lnk")
    
    # Create a shell object
    shell = Dispatch('WScript.Shell')
    
    # Create the shortcut object
    shortcut = shell.CreateShortCut(shortcut_path)
    
    # Set the target path of the shortcut
    shortcut.Targetpath = executable_path
    shortcut.WorkingDirectory = os_path.dirname(executable_path)  # Optional: Set the working directory
    shortcut.IconLocation = executable_path  # Optional: Set the icon of the shortcut to the executable icon
    shortcut.save()
    
    return startup_folder