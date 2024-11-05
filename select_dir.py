# %% MODULE IMPORTS

import asyncio
from tkinter import Tk, filedialog

# %% FUNCTIONS

async def select_folder():
    loop = asyncio.get_event_loop()
    
    def run_in_thread():
        root = Tk()
        root.withdraw()  # Hide the main window
        dirname = filedialog.askdirectory(parent=root, initialdir="/", title="Please select the 'WTF' directory")
        root.destroy()  # Close the tkinter window
        return dirname

    # Run the folder selection in a separate thread
    dirname = await loop.run_in_executor(None, run_in_thread)
    return dirname