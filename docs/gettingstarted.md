# Getting Started with Website Tracker

## Installation
- [Installing Python package](#installing-python-package)
- [Creating Discord bot](#creating-discord-bot)
- [Setting up configuration](#setting-up-configuration)

## Usage
- [Bot Deployment](#bot-deployment)
- [Bot Commands](#bot-commands)

<a name="installing-python-package"></a>
## 1. Installing the Python package dependencies

To install the Python package dependencies you have to type `pip install -r requirements.txt` into the command prompt which already cd into the project directory.


<a name="creating-discord-bot"></a>
## 2. Creating Discord Bot

You can create a Discord bot through [[Discord.py Guild]](https://discordpy.readthedocs.io/en/stable/discord.html).

The following bot permissions are required.
   ![alt text](/docs/imgs/discord-bot-permission-requirement.png)

The bot token will make use of [the next part](#setting-up-configuration).

***Notice that please keep your bot token as a top secret in order to prevent others from takeover your bot and doing any malicious things.**

<a name="setting-up-configuration"></a>
## 3. Setting up configuration

You must be done the following steps before using the bot.

1. Make a copy of the `config.example.toml`.
2. Rename the copied file to `config.toml`.
3. Open `config.toml` with any text editor you like.
4. Copy and paste the Discord bot token to `discord_bot_token`.
5. Paste the channel ID where your world like to run to `discord_bot_channel_id`.
   * In order to find the channel ID, you have to switch on the `Developer Mode` which is located in [User Setting > Advanced]
   * Then you can find `Copy ID` when you right-click to the channel.
   
      ![alt text](/docs/imgs/discord-copy-channel-id.png)
6. Save the config file.

<a name="bot-deployment"></a>
## 4. Bot Deployment

1. Run `py main.py` in the command prompt.
2. Check if you received the bot online message on the channel which you specify in `discord_bot_channel_id`.
3. If yes the bot is good to go. If not, please make sure you follow all the steps that mention in [[Installation]](#installing-python-package).

<a name="bot-commands"></a>
## 5. Bot Commands

Tips [>track] or in short [>tk]

1. `>track {url-0} {url-1(optional)} {url-2(optional)}...` Track any website by the url(s).
2. `>track add {category(optional)} {url-0} {url-1(optional)}...` Add url(s) to the tracking list.
3. `>track remove {category(optional)} {url-0} {url-1(optional)}...` Remove url(s) from the tracking list.
4. `>track catremove {category-0} {category-1(optional)}...` Remove category.
5. `>track catrename {old-category-name} {new-category-name}` Rename category.
6. `>track list {category-0(optional)} {category-1(optional)}...` List out the tracking list.
7. `>track report {category-0(optional)} {category-1(optional)}...` Create a tracking report.
8. `>help` Say for help.
