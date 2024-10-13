# Ascension TSM Data Sharing App

[Trade Skill Master](https://tradeskillmaster.com/) data sharing application for [Ascension WoW's](https://ascension.gg/) [TSM Addon](https://github.com/Ascension-Addons/TradeSkillMaster).

You can get a hold of me on [SzylerAddons Discord](https://discord.gg/uTxuDvuHcn) (Addons from Szyler and co --> #tsm-data-sharing) - @the_real_mortificator.

Thanks to [Szyler](https://github.com/Szyler) and [MummieSenpai](https://github.com/MummieSenpai) for testing.

&nbsp;

> [!CAUTION]
> Will most likely be blocked by Windows Defender / Antivirus software
> 
> READ FAQ

&nbsp;

## What it does - TLDR
Periodically checks for a change to scanned data, uploads the latest to the database and downloads the latest to your local PC, mimicking what the official TSM app (used on retail WoW) does. As they describe it: "keeps your addon data up-to-date".<br>
In other words, you will always have access to the most recent prices.<br>

## What it does - non-TLDR
When first run, it will ask you whether you want to create a scheduled task to run the app on startup (input Y or N in the console and press Enter). This will happen only when first running the script. The idea behind it running on startup is due to the fact that we can only update data in the WTF folder when Ascension is not running, because each /reload, logout to char select or game restart automatically writes to the files (ie it would rewrite what we put there). Hence whenever you launch Ascension you will have the latest data there is. More info in the FAQ section below.<br>
When first run, it will also create `update_times.json` in the directory where the EXE file is saved which tracks what LUA file got last updated. Don't mess with this file.

There are two core functionalities:<br>
- Data download
  - Downloads newest data from the DB.
  - Happens ONLY when Ascension is not running and is being downloaded every 15 minutes.
- Data upload
  - When you do a scan, could be partial or full, please do a /reload when you can. This will make the game write to the LUA file, get detected by the app and uploaded to the DB.
  - The script checks for changes every 5 minutes.

&nbsp;

> [!WARNING]
> Currently only available for Windows.

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

To allow this file in Windows Defender, do this:<br>
![windows-defender_updated](https://github.com/user-attachments/assets/f8a023cd-5a8e-4202-9df8-b07889711eb6)

If an Antivirus blocks the file, put whitelist the folder you saved the EXE to, eg:<br>
![image](https://github.com/user-attachments/assets/17e55557-479a-4574-9664-de7ba3ab3f19)<br>
![image](https://github.com/user-attachments/assets/bcbf156d-8f6e-47ed-88d5-d60f20dcdbfc)


&nbsp;

- Q: Can I run it using Python instead of the EXE?
- A: Unfortunately no. There are crucial files missing from the repo, like server endpoints, hash-salting mechanism, etc.

&nbsp;

- Q: The code did not find the WTF folder, then asked me to find it myself.
- A: The code will look at the default install location as well as other frequently used. If you used another install loc, you have to find it and select the WTF folder like so:<br>
![folder_select](https://github.com/user-attachments/assets/de21a600-1f00-4c40-b91c-47f4f9e53a10)


&nbsp;

- Q: What data gets sent to the DB?
- A: Hashed account name and TSM scan (item) data. Nothing else.

&nbsp;

- Q: Are multiple accounts supported?
- A: Yes. The code will only upload the latest data per realm regardless of account.

&nbsp;

- Q: Why a scheduled task and not a shortcut in the Startup folder? That would be easier...
- A: We tried, however since the app has to run as admin, it will not be launched on startup via a shortcut, hence a scheduled task.

&nbsp;

- Q: What if I reinstal Ascension to other location, mess with Ascension folder structure, change my mind about running on startup etc?
- A: Just delete `update_times.json`. That will re-trigger the initial setup.

&nbsp;

- Q: What if I want delete the startup task manually without deleting `update_times.json`?
- A: Start - find Task Scheduler - select "TSM Data Sharing App" and click Delete:<br>
![task_scheduler_delete](https://github.com/user-attachments/assets/11a8a17f-d83c-4926-bdf4-e9df4888214f)

&nbsp;

- Q: How do I know which version of the app I have?
- A: Hover over the exe. Or right click it and select Properties and then check the metadata in the Details tab. Or just check the log files - the naming convention is `ascension_tsm_data_sharing_app_v{VERSION}_{YEARMONTHDAY_HOURMINUTESECOND}.log`

&nbsp;

- Q: Why not put the version in the name of the exe?
- A: Due to the scheduled task. Once upgraded, the file name in the task scheduler would still point to the old file, so you would have to re-trigger the initial setup.

&nbsp;

- Q: How do I know there is a new release? Do I have to keep checking github?
- A: No you don't. When there's a new version, the app will let you know directly in the console as well as with a windows' toast notification with a convenient button that brings you directly to the release section here. To do so, go to Start - Notifications & Actions - Notifications - Enable.<br>
![toast_notif](https://github.com/user-attachments/assets/1323bc01-8eda-4a2c-bda4-38086048bf66)

&nbsp;

- Q: The app crashed on me / apparently doesn't work as intended. What should I do?
- A: Definitely report it. Create an issue here, if you have a github account, or alternatively you can try [SzylerAddons Discord](https://discord.gg/uTxuDvuHcn) --> Addons from Szyler and co --> #tsm-data-sharing. Either way, describe the issue in detail and include logs. For questions head to Discord.

&nbsp;

- Q: Will this support Linux?
- A: Not sure. I'm losing interested in Ascension atm. If there's enough demand, I'll consider it.
