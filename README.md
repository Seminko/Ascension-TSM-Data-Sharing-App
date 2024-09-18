# Ascension TSM Data Sharing App

[Trade Skill Master](https://tradeskillmaster.com/) application for [Ascension WoW](https://ascension.gg/).

&nbsp;

> [!CAUTION]
> Will most likely be blocked by Windows Defender / Antivirus software
> 
> READ FAQ

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

> [!WARNING]
> Currently only available for Windows and Area 52 realm.

> [!IMPORTANT]
> To keep this going, we each need to do our part with scanning and /reload-ing from time to time.

&nbsp;

## FAQ
- Q: Why an EXE file? I don't like that!
- A: So that it's accessible for most ppl, even those without python knowledge.

&nbsp;

- Q: Why is the EXE so big? It looks suspicious!
- A: Because pyinstaller has to bundle all dependencies to the EXE file.

&nbsp;

- Q: Why does it require Admin rights? It looks even more suspicious!
- A: Because the LUA files saved in the default directory (`\Program Files\Ascension Launcher\`) can be updated only with admin rights. Without giving this app admin rights as well, we wouldn't be able to update the LUA files.

&nbsp;

- Q: Windows defender says it protected my PC / My Antivirus moved the file to quarantine! I knew it!
- A: Windows defender will flag all unsigned apps. To get the app signed requires a form of approval, which you have to request. It takes time and costs money (there is a free version but each code change would have to be approved again an again, and we would wait again and again). Antivirus software works similarly. Also, since we have a single EXE, the compiler has to include all the dependencies (ie modules / libraries like the re module used for regex) into the single file and WD / Antivirus don't like that because viruses / malware do the same. However, you can see 99% of the code here on GitHub so those who can read python can confirm there's nothing nefarious going on here. (The last 1% is explained in the point below)

To allow this file in Windows Defender, do this:
![windows-defender_updated](https://github.com/user-attachments/assets/f8a023cd-5a8e-4202-9df8-b07889711eb6)

If an Antivirus blocks the file, put whitelist the folder you saved the EXE to, eg:
![image](https://github.com/user-attachments/assets/17e55557-479a-4574-9664-de7ba3ab3f19)
![image](https://github.com/user-attachments/assets/bcbf156d-8f6e-47ed-88d5-d60f20dcdbfc)


&nbsp;

- Q: Can I run it using Python instead of the EXE?
- A: Unfortunately no. There are crucial files missing from the repo, like server endpoints, hash-salting mechanism, etc.

&nbsp;

- Q: The code did not find the WTF folder, then asked me to find it myself. I don't know where it is. Where can I find it?
- A: The code will look at the default install location as well as other frequently used. If you used another install loc, you have to find it and select the WTF folder like so:
![folder_select](https://github.com/user-attachments/assets/de21a600-1f00-4c40-b91c-47f4f9e53a10)


&nbsp;

- Q: What data gets sent to the DB?
- A: Hashed account name and TSM item data. Nothing else.

&nbsp;

- Q: Are multiple accounts supported?
- A: Yes. The code will only upload the latest data per realm regardless of account. (Currently only supports Area 52 until properly tested.)

&nbsp;

- Q: Will this support realms other than Area 52 soon?
- A: Yes.

&nbsp;

- Q: Will this support Linux?
- A: Once we iron things out for Windows I'm open to it.

&nbsp;

- Q: What if I reinstal Ascension to other location or mess with Ascension folder structure?
- A: Just delete `update_times.json`. That will re-trigger "the setup" and will try to find / ask for the WTF folder again.
