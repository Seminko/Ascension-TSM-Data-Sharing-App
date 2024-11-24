# Ascension TSM Data Sharing App

[Trade Skill Master](https://tradeskillmaster.com/) data sharing application for [Ascension WoW's](https://ascension.gg/) [TSM Addon](https://github.com/Ascension-Addons/TradeSkillMaster).

You can get a hold of me on [SzylerAddons Discord](https://discord.gg/uTxuDvuHcn) (Other DEVs Addons (N-Z) --> #tsm-data-sharing) - @the_real_mortificator.

Thanks to [Szyler](https://github.com/Szyler) and [MummieSenpai](https://github.com/MummieSenpai) for testing.

&nbsp;

> [!IMPORTANT]
> You can download the EXE from the [Releases page](https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/releases).

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

## Check out FAQ
[Wiki FAQ](https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/wiki/FAQ)
