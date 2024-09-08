# import tkinter as tk        # Tkinter is now tkinter (lowercase)
from tkinter import Tk
from tkinter import filedialog  # tkFileDialog is now filedialog

def select_folder():
    root = Tk()
    root.withdraw()  # This hides the main window, you only want the dialog
    
    dirname = filedialog.askdirectory(parent=root, initialdir="/", title="Please select the 'WTF' directory")
    
    return dirname

# kek = select_folder()
# if not kek.endswith(r"/client/WTF"):
#     raise ValueError("Selected wrong folder.")
# # if you click Cancel an empty string is returned
# print(f"'{kek}'")