# Ascension TSM Data Sharing App

> [!WARNING]
> Currently only available for Windows and Area 52 realm.

## What it does - TLDR
Periodically checks for a change to scanned data, uploads the latest to the database and downloads the latest to your local PC, mimicking what the official TSM app (used on retail WoW) does. As they describe it: "keeps your addon data up-to-date".<br>
In other words, you will always have access to the most recent prices.<br>

## What it does - non-TLDR
When first run, it will create `update_times.json` in the directory where the EXE file is saved which tracks what file got last updated.

It will also create a shortcut to the exe in your Startup folder (this one: `C:\Users\{USERNAME}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`). This will ensure the app runs when you turn on your pc.<br>
If you don't like this and would rather run the app manually, feel free to remove the shortcut - it will not be created again (as long as you don't delete the update_times.json).<br>
The idea behind it running on startup is due to the fact that we can only update data in the WTF folder when Ascension is not running, because each /reload, logout to char select or game restart automatically writes to the files (ie it would rewrite what we put there). Hence whenever you launch Ascension you will have the latest data there is.

&nbsp;

There are two core functionalities:<br>
- New data download
  - Downloads newest data from the DB.
  - Happens ONLY when Ascension is not running and is being downloaded every hour.
- New data upload
  - When you do a scan, could be partial or full, please do a /reload when you can. This will make the game write to the LUA   file, get detected by the app and uploaded to the DB.
  - The script checks for changes every 5 minutes.

&nbsp;

> [!IMPORTANT]
> To keep this going, we each need to do our part with scanning and /reload-ing from time to time.

&nbsp;

## FAQ
- Q: Why an EXE file?
- A: So that it's accessible for most ppl, even those without python knowledge.

&nbsp;

- Q: Why does it require Admin rights? It looks even more suspicious!
- A: Because the LUA files saved in the default directory (\Program Files\Ascension Launcher\) can be updated only with admin rights. Without giving this app admin rights as well, we wouldn't be able to update the LUA files unless we closed the launcher first.

&nbsp;

- Q: Why is the endpoint the data is being sent to / downloaded from removed from the source code? I would like to run it using Python.
- A: Just to make it a smidge harder for ppl to mess with things.

&nbsp;

- Q: Why is the EXE so big? It looks suspicious!
- A: Because pyinstaller has to bundle all dependencies to the EXE file and also I have little experience with it.

&nbsp;

- Q: The code did not find the WTF folder, then asked me to find it myself. I don't know where it is. Where can I find it?
- A: Find the Ascension Launcher folder, it's under here: `Ascension Launcher\resources\client\WTF`

&nbsp;

- Q: What data gets sent to the DB?
- A: Hashed account name and TSM item data. Nothing else.

&nbsp;

- Q: Are multiple accounts supported?
- A: Yes. The code will only upload the latest data per realm regardless of account. (Currently only supports Area 52 until properly tested.)

&nbsp;

- Q: Will this support Linux?
- A: Once we iron things out for Windows I'm open to it.

&nbsp;

- Q: Will this support other realms soon?
- A: Yes.

&nbsp;

- Q: What if I reinstal Ascension to other location?
- A: Just delete `update_times.json`. That will re-trigger "the setup" and will try to find / ask for the WTF folder again.
