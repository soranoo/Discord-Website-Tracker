import time
import os
import re
import colorama
import toml
import requests
import validators
import asyncio
import pandas as pd
import numpy as np

import discord
from discord.ext import commands
from discord_components import DiscordComponents, ComponentsBot, Button

from datetime import datetime
from tcp_latency import measure_latency
from urllib.parse import urlparse

from src.logger import log, color_log
from src import eventSystem, utility, TableIt


# ---------------* Common *---------------
config = toml.load("config.toml")
color_log = config.get("color_log")
discord_bot_token = config.get("discord_bot_token")
discord_bot_command_prefix = config.get("discord_bot_command_prefix")
discord_bot_channel_id = config.get("discord_bot_channel_id")
periodic_tracking_frequency = config.get("periodic_tracking_frequency")
website_offline_notification = config.get("website_offline_notification")

# ---------------* Data Storage *---------------
def load_csv(folderPath=os.getcwd(), fileName="db.csv"):
	if os.path.exists(folderPath+"/"+fileName):
		log.ok(f"Loaded <{fileName}> from <{folderPath}>")
		df = pd.read_csv(fileName)
	else:
		log.ok(f"Created <{fileName}> in <{folderPath}>")
		initialCategory = {"main":[]}
		df = pd.DataFrame(initialCategory)
	return df

def cleanup_data(df):
    dict = {}
    categories = df.columns
    for category in categories:
        dict.update({category:df[category].drop_duplicates(keep="first")})
    df = pd.DataFrame(dict)
	# credit: https://stackoverflow.com/a/52622603
    temp = df.isnull().values
    out = df.values[np.argsort(temp, axis=0, kind='mergesort'), np.arange(temp.shape[1])]
    df = pd.DataFrame(out, columns=df.columns)
    return df

def save_csv(df, fileName="db.csv"):
    df.to_csv(fileName,index=False)
    log.ok("Successfully saved urls data.")

def store_url(df, category, url):
    if "/" not in url[-1]:
        url += "/"

    if category in df.columns:
        df = df.append({category:url}, ignore_index=True)
        log.ok(f"Successfully stored <{url}> to category of <{category}>")
    else:
        log.warning(f"Store failed, reason: category of <{category}> dose not exist.")
        try:
            cell = [url,]
            for i in range(0,len(df["main"])-len(cell)):
                cell.append(np.nan)
            df[category] = cell
            log.ok(f"Successfully created category of <{category}>.")
        except Exception as err:
            log.error(err)
            log.error(f"Failed to create category of <{category}>.")
            return False
        log.ok(f"Successfully stored <{url}> to category of <{category}>")
    df = cleanup_data(df)
    print(df)
    save_csv(df)
    return True

def remove_url(df, targetCategory, url):
    dict = {}
    categories = df.columns
    if targetCategory not in categories:
        log.warning(f"Remove <{url}> failed, reason: category of <{targetCategory}> dose not exist.")
        return False

    for category in categories:
        dict.update({category:df[category]})
    for category in dict.keys():
        if category == targetCategory:
            if url in df[category].values:
                try:
                    dict[category] = dict[category].replace({url:np.nan})
                    log.ok(f"Successfully removed <{url}> from category of <{category}>")
                except Exception as err:
                    log.error(err)
                    log.error(f"Remove <{url}> failed from category of <{targetCategory}>.")
                    return False
            else:
                log.warning(f"<{url}> dose exist in category of <{targetCategory}>.")
    df = pd.DataFrame(dict)
    print(df)
    save_csv(df)
    return True

def fetch_urls(df, category):
    if category not in df:
        log.warning(f"Fetch urls failed, reason: category of <{category}> dose not exist.")
        return False
    urls = []
    df = df.fillna("none")
    for url in df[category]:
        if url == "none":
            continue
        urls.append(url)
    return urls

# ---------------* Main *---------------
def check_web_connection(url, timeout=5):
    log.info(f"Checking <{url}> connection...")
    try:
        request = requests.get(url, timeout=timeout)
        log.ok(f"[online] Successfully connected to <{url}>")
        return True
    except (requests.ConnectionError, requests.Timeout) as exception:
        log.warning(f"[offline] Failed to connect <{url}>")
        return False

def get_web_latency(url):
    regularExpressions = re.compile(r"https?://(www\.)?") # regular expressions
    parsed = urlparse(url)
    urlPort = None if parsed.port is None else f":{parsed.port}"
    if urlPort is not None:
        url = url.replace(urlPort,"")
    try:
        latency = measure_latency(host=regularExpressions.sub("", url).strip().strip("/"), port=80 if parsed.port==None else parsed.port)
        return latency
    except Exception as err:
        return False

def create_report(df, targetCategory=None):
    log.info("Creating report...")
    report = {}
    table = [["category", "url", "connection", "latency"]]
    for category in df.columns:
        report.update({category:[]})
        if not targetCategory or (category == targetCategory):
            for url in fetch_urls(df, category):
                connection = check_web_connection(url)
                latency = round(utility.avg(get_web_latency(url))) if connection else False
                report[category].append({"url":url, "connection":connection, "latency":latency})
                table.append([category, url, connection, latency])
    TableIt.printTable(table, useFieldNames=True)
    return report

def create_dc_tracking_signal(url, connection, latency):
    if connection:
        if latency:
            latencySignal = ":green_circle:" if latency <= 200 else ":yellow_circle:"
            msg = f"{latencySignal}  **>[{utility.round_to_n(latency,3)}ms]>**  <{url}>"
        else:
            msg = f":green_circle:  **>>>>>>>>>**  <{url}>"
    else:
        msg = f":red_circle:  **>>>>>>>>>**  <{url}>"
    return msg

async def periodic_tracking():
    await discord_bot.wait_until_ready()
    channel = discord_bot.get_channel(discord_bot_channel_id)

    while not discord_bot.is_closed():
        # update bot status, credit: https://stackoverflow.com/a/59126629
        await discord_bot.change_presence(activity=discord.Game(name="Periodic Tracking..."))

        log.info("Start Periodic Tracking...")
        df = load_csv()
        reportRawData = create_report(df)
        lostConnect = {}
        msg = "Lost Connect...\n\n"
        for category, data in reportRawData.items():
            lostConnect.update({category:[]})
            for trackingData in data:
                if not trackingData["connection"]:
                    lostConnect[category].append(trackingData['url'])
        lostConnectNum = 0
        for category, urls in lostConnect.items():
            if len(urls) == 0:
                continue
            lostConnectNum += len(urls)
            msg += f"**{category}**\n"
            for url in urls:
                msg += f"{url}\n"
        if lostConnectNum > 0:
            await channel.send(f"{'@here' if website_offline_notification else ''}", embed=create_embeds_msg(10181046, "", f":exclamation: **[Offline Notification]**\nThere {'are' if lostConnectNum > 1 else 'is'} {lostConnectNum} website{'s' if lostConnectNum > 1 else ''} offline. \n```{msg}```"))
        log.ok(f"Periodic Tracking finished.")
        log.info(f"Next Periodic Tracking will after {periodic_tracking_frequency}s.")

        # update bot status, credit: https://stackoverflow.com/a/59126629
        await discord_bot.change_presence(activity=discord.Game(name="Stand-By..."))

        await asyncio.sleep(periodic_tracking_frequency) # repeat after every xx seconds




# ---------------* Discord Bot *---------------
discord_bot = commands.Bot(command_prefix=discord_bot_command_prefix)
DiscordComponents(discord_bot)

def create_embeds_msg(color, title, description):
    # color: https://gist.github.com/thomasbnt/b6f455e2c7d743b796917fa3c205f812
    embed=discord.Embed(
        title=title,
        description=description,
        color=color,)
    return embed

@discord_bot.event
async def on_ready():
    log.ok("Logged in as '{0.user}'".format(discord_bot))
    log.info(">> Bot is READY <<")
    channel = discord_bot.get_channel(discord_bot_channel_id)
    await channel.send("> I am back~  :tada:\n@here")
    await asyncio.sleep(15)
    discord_bot.loop.create_task(periodic_tracking()) # start periodic tracking

@discord_bot.event
async def on_message(msg):
    if msg.author == discord_bot.user:
        return

    if discord_bot_command_prefix in msg.content[0:1]:
        log.info(f"User: {msg.author} tried to do command '{msg.content}'")
        await msg.add_reaction("✅")
        await discord_bot.process_commands(msg) # run command
    else:
        await msg.add_reaction("❌")
        await msg.channel.send("> :exclamation:  IDK wt u said.")
    


@discord_bot.command(aliases=["Ping"])
async def ping(ctx):
        await ctx.send(f"> {round(discord_bot.latency*1000)} ms")

@discord_bot.command(aliases=["Track", "tk"])
async def track(ctx, *args):
    if len(args) == 0:
        await ctx.send("> :warning:   Command Error.")
        await ctx.send("> :information_source:   **It should be...** ```>track {url}```")
        return

    subCmds = ["add", "remove", "catremove","catrename", "list", "report"]
    if args[0].lower() in subCmds:
        args = list(args) # convert tuple to list
        subcmd = args[0]
        if subcmd == "add": # command structure: >track add(args0) category(args1) url(args2-)
            if len(args) >= 2:
                if validators.url(args[1]):
                    newArgs = []
                    for id, value in enumerate(args):
                        newArgs.append(value)
                        if id == 0:
                            newArgs.append("main")
                    args = newArgs
            else:
                if len(args) > 1:
                    if not validators.url(args[1]):
                        await ctx.send(f"> :warning:   Non-valid URL <**{args[1]}**> (Malformed?)")
                        await ctx.send(f"> :information_source:   **Valid URL example ~** ```https://url.com```")
                        return
                else:
                    await ctx.send("> :warning:   Command Error.")
                    await ctx.send("> :information_source:   **It should be...** ```>track add {category(optional)} {url}```")
                    return

            targetCategory = args[1]
            urls = args
            del urls[0] # remove "add"
            del urls[0] # remove category
            for url in urls:
                if not validators.url(url):
                    await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Failed to add <{url}> to the tracking list.\nreason: non-valid URL <{url}> (Malformed?)"))
                    await ctx.send(f"> :information_source:   **Valid URL example ~** ```https://url.com```")
                    continue

                categories = load_csv().columns
                if targetCategory in categories:
                    if store_url(load_csv(),targetCategory, url):
                        await ctx.send(embed=create_embeds_msg(5763719, "", f"✅  Successfully stored <{url}> to category of <**{targetCategory}**>"))
                    else:
                        await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Failed to add <{url}> to the tracking list."))
                else:
                    await ctx.send(f"> Category of <{targetCategory}> not exist. Would you like to create it?", components=[
                        [Button(label="YES", style="3", emoji="✅", custom_id="btn_yes"),
                        Button(label="NO", style="4", emoji="❌", custom_id="btn_no")]
                    ])
                    interaction = await discord_bot.wait_for("button_click")
                    if interaction.custom_id == "btn_yes":
                        if store_url(load_csv(),targetCategory, url):
                            await interaction.send(embed=create_embeds_msg(5763719, "", f"✅  Successfully created category of <{targetCategory}>."), ephemeral=False)
                            await ctx.send(embed=create_embeds_msg(5763719, "", f"✅  Successfully stored <{url}> to category of <**{targetCategory}**>"))
                        else:
                            await interaction.send(embed=create_embeds_msg(15548997, "", f":warning:  Failed to create category of <{targetCategory}>."), ephemeral=False)
                            await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Failed to add <{url}> to category of <**{targetCategory}**>."))
                    elif interaction.custom_id == "btn_no":
                        await interaction.send(embed=create_embeds_msg(15548997, "", f":warning:  Remove <{url}> failed from category of <{targetCategory}>."), ephemeral=False)
        elif subcmd == "remove":
            if len(args) >= 2:
                if validators.url(args[1]):
                    newArgs = []
                    for id, value in enumerate(args):
                        newArgs.append(value)
                        if id == 0:
                            newArgs.append("main")
                    args = newArgs
            else:
                if len(args) > 1:
                    if not validators.url(args[1]):
                        await ctx.send(f"> :warning:   Non-valid URL <**{args[1]}**> (Malformed?)")
                        await ctx.send(f"> :information_source:   **Valid URL example ~** ```https://url.com```")
                        return
                else:
                    await ctx.send("> :warning:   Command Error.")
                    await ctx.send("> :information_source:   **It should be...** ```>track remove {category(optional)} {url}```")
                    return

            targetCategory = args[1]
            urls = args
            del urls[0] # remove "remove"
            del urls[0] # remove category
            for url in urls:
                if not validators.url(url):
                    await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Remove <{url}> failed from category of <**{targetCategory}**>.\nreason: non-valid URL <{url}> (Malformed?)"))
                    await ctx.send(f"> :information_source:   **Valid URL example ~** ```https://url.com```")
                    continue
                
                df = load_csv()
                categories = df.columns
                if targetCategory in categories:
                    if url in df[targetCategory].values:
                        if remove_url(df, targetCategory, url):
                            await ctx.send(embed=create_embeds_msg(5763719, "", f"✅  Successfully removed <{url}> from category of <**{targetCategory}**>"))
                        else:
                            await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Remove <{url}> failed from category of <**{targetCategory}**>."))
                    else:
                        await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  <{url}> dose exist in category of <**{targetCategory}**>."))
                else:
                    await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Remove <{url}> failed from category of <**{targetCategory}**>\nreason: category of <**{targetCategory}**> not exist."))
        elif subcmd == "catremove":
            if len(args) == 1:
                await ctx.send("> :warning:   Command Error.")
                await ctx.send("> :information_source:   **It should be...** ```>track catremove {category}```")
                return
            targetCategories = args
            del targetCategories[0] # remove "catremove"
            for category in targetCategories:
                if category == "main":
                    await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Category of <**{category}**> cannot be removed."))
                    continue
                df = load_csv()
                if category in df.columns:
                    try:
                        df = df.drop(columns=[category])
                        log.ok(f"Successfully removed category of <{category}>")
                        await ctx.send(embed=create_embeds_msg(5763719, "", f"✅  Successfully removed category of <**{category}**>"))
                        save_csv(df)
                    except Exception as err:
                        await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Failed to remove category of <**{category}**>."))
                        await ctx.send(f"ERROR code-```{err}```")
                        log.error(err)
                        log.error(f"Category of <{category}> cannot be removed.")
                else:
                    await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Category of <**{category}**> does not exist."))
        elif subcmd == "catrename":
            if len(args) <= 2:
                await ctx.send("> :warning:   Command Error.")
                await ctx.send("> :information_source:   **It should be...** ```>track catrename {old-category-name} {new-category-name}```")
                return
            oldName = args[1]
            newName = args[2]
            if oldName == "main":
                await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  <**{oldName}**> cannot be renamed."))
                return
            df = load_csv()
            try:
                df = df.rename({oldName:newName}, axis='columns')
                save_csv(df)
                await ctx.send(embed=create_embeds_msg(5763719, "", f"✅  Successfully renamed category name from <**{oldName}**> to <**{newName}**>."))
                log.ok(f"Successfully renamed category name from <{oldName}> to <{newName}>.")
            except Exception as err:
                log.error(err)
                log.error(f"Failed to rename category name from <{oldName}> to <{newName}>.")
                await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Failed to rename category name from <**{oldName}**> to <**{newName}**>."))
        elif subcmd == "list":
            df = load_csv()
            categories = df.columns
            if len(args) == 1:
                targetCategories = categories
            else:
                targetCategories = args
                del targetCategories[0] # remove "list"
            msg = "TRACKING LIST-\n\n"
            for category in targetCategories:
                if category not in categories:
                    await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Category of <**{category}**> does not exist."))
                    continue
                urls = fetch_urls(df, category)
                msg += f"**{category}** ({len(urls)})\n"
                if len(urls) == 0:
                    msg += "{empty}\n"
                    continue
                for index, url in enumerate(urls):
                    msg += f"{index} {url}\n"
            await ctx.send(f"```{msg}```")
        elif subcmd == "report":
            await ctx.send(f"> Please wait...")
            df = load_csv()
            categories = df.columns
            reportRawData = {}
            if len(args) == 1:
                reportRawData = create_report(df)
            else:
                targetCategories = args
                del targetCategories[0] # remove "report"
                for category in targetCategories:
                    if category not in categories:
                        await ctx.send(embed=create_embeds_msg(15548997, "", f":warning:  Category of <**{category}**> does not exist."))
                        continue
                    reportRawData.update(create_report(df, category))
            if len(reportRawData) == 0:
                return
            report = "\n"
            for category, data in reportRawData.items():
                report += f"\n**{category}**\n"
                if len(data) == 0:
                    report += "{empty}"
                for trackingData in data:
                    trackingSignal = create_dc_tracking_signal(trackingData["url"], trackingData["connection"], trackingData["latency"])
                    report += f"{trackingSignal}\n"
            await ctx.send(embed=create_embeds_msg(1752220, "TRACKING REPORT", f"{report}"))
    else: # instant track
        await ctx.send(f"> Please wait...")
        for url in args:
            if validators.url(url):
                if check_web_connection(url):
                    webLatency = get_web_latency(url)
                    await ctx.send(embed=create_embeds_msg(1752220, "", f"{create_dc_tracking_signal(url, check_web_connection(url), utility.round_to_n(utility.avg(webLatency),3))}"))
                else:
                    await ctx.send(embed=create_embeds_msg(1752220, "", f"{create_dc_tracking_signal(url, False, False)}"))
            else:
                await ctx.send(f"> :warning:   Non-valid URL <**{url}**> (Malformed?)")
                await ctx.send(f"> :information_source:   **Valid URL example - ```https://url.com```**")

            


# ---------------* Initialization *---------------
# discord_bot.loop.create_task(periodic_tracking()) # start periodic tracking
discord_bot.run(discord_bot_token) # start bot
