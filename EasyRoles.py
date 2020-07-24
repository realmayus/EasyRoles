import asyncio  # for waiting before changing the status of the bot
import configparser  # for reading the config which contains bot token and prefix
import datetime
import shlex  # for parsing the named arguments in the ::selfrole command
import sys
import logging
import time
from logging.handlers import RotatingFileHandler

import firebase_admin  # for working with the Firestore database
import discord  # for interacting with the discord API
from discord.ext import commands  # for creating and using commands easily!
from firebase_admin import credentials  # for connecting with the database
from firebase_admin import firestore  # for working with the database

#############
"""LOGGING"""
#############
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
logFile = 'log.txt'
my_handler = RotatingFileHandler(filename=logFile, mode='w', maxBytes=5*1024*1024, backupCount=2, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)
logger = logging.getLogger("easyroles")
logger.setLevel(logging.INFO)
logger.addHandler(my_handler)


def exception_handler(_type, value, _tb):
    logger.exception("Uncaught exception: " + str(value))


def output(*msg):
    logger.info(' '.join(msg))
    print(' '.join(msg))


sys.excepthook = exception_handler
############

config = configparser.RawConfigParser()
config.read("config.ini")

# Stats
start_time = time.time()
stats_roles_given = 0
stats_roles_revoked = 0


# Setting the command prefix to the config value if it exists, else use :: as default
prefix = config["bot"]["prefix"] if config.has_option("bot", "prefix") else "::"
bot = commands.Bot(command_prefix=prefix)

# Available config options
available_options_and_values = {
    "replace_existing_roles": ["false", "true"],
    "forbid_invite": ["false", "true"]
}

firebase_cred = credentials.Certificate("firebase-sdk.json")  # Obtaining certificate from ./firebase-sdk.json
firebase_admin.initialize_app(firebase_cred)  # Initializing firebase app with credentials
db = firestore.client()

cached_selfrole_msgs = []  # Cache for the selfrole msgs so that we don't have to make a damn DB call every damn time the user reacts to any damn message in any damn server the damn bot is in. Damn.

cached_config_options = []  # Cache for all config options in all servers so we don't have to make a DB call every time the user reacts to a msg T_T


@bot.event
async def on_ready():
    """Caching both guild-specific config options and all registered selfroling messages"""
    global cached_config_options  # ugly, ik
    output("Bot logged in!")

    
async def cache(callback_channel=None):
    output("Caching config options of all servers…")
    docs = db.collection("guild_config").stream()
    for doc in docs:
        cache = {"guild_id": doc.id}
        values = doc.to_dict()
        for key, value in values.items():
            cache[key] = value
        cached_config_options.append(cache)
    output("Done!")

    output("Now caching all selfroling messages for all guilds.")
    i = 0
    for channel_coll in db.collections():
        if channel_coll.id != "guild_config":
            channel_id = channel_coll.id
            i += 1
            output("-> Caching selfroling messages for channel no. " + str(i))
            for doc in channel_coll.stream():
                if doc.exists:  # check if message is registered selfrole message :3
                    values = doc.to_dict()
                    cached_selfrole_msgs.append(
                        {"channel_id": channel_id, "message_id": doc.id, "mention_id": values["mention_id"],
                         "emoji": values["emoji"]})  # add the message from the DB to our cache ʕ•ᴥ•ʔ

    output("Done! Bot is now ready for use.")


async def status_task():
    """interactive status, changes from ::help to the credit and back"""
    await bot.wait_until_ready()
    while True:
        await asyncio.sleep(7*60)
        await bot.change_presence(activity=discord.Game(name=prefix + "help"))
        await asyncio.sleep(7*60)
        await bot.change_presence(activity=discord.Game(name=prefix + "inviteme"))


@bot.command()
async def inviteme(ctx):
    """Sends an invite link to the chat so that you can invite the bot to your server! There's a flag to have the bot send the invite via DM if you don't want to have it posted in your server."""
    option = next((item for item in cached_config_options if str(item["guild_id"]) == str(ctx.guild.id)), None)
    if option:
        if "forbid_invite" in option.keys():
            if option["forbid_invite"] == "true":
                try:
                    await ctx.author.send("You can invite me to your server if you like what I can do! <3\n <https://discord.com/api/oauth2/authorize?client_id=710438395830206485&permissions=8&scope=bot>")
                except discord.errors.Forbidden:
                    await ctx.send("😞  Invite links aren't allowed in here and I couldn't send you one via DM, please `allow direct messages from server members` in your privacy settings for this server.")
                else:
                    await ctx.send("Please check your DMs, I'm not allowed to send invite links in here 😞")
            else:
                await ctx.send(
                    "You can invite me to your server if you like what I can do! <3\n <https://discord.com/api/oauth2/authorize?client_id=710438395830206485&permissions=8&scope=bot>")
        else:
            await ctx.send(
                "You can invite me to your server if you like what I can do! <3\n <https://discord.com/api/oauth2/authorize?client_id=710438395830206485&permissions=8&scope=bot>")
    else:
        await ctx.send(
            "You can invite me to your server if you like what I can do! <3\n <https://discord.com/api/oauth2/authorize?client_id=710438395830206485&permissions=8&scope=bot>")


# @bot.command()
# @commands.cooldown(1, 1200, commands.BucketType.guild)
# async def recache(ctx):
#     """Reloads the cache for every server. Useful if things don't work as they should. Has a cooldown of 20 minutes per guild. Do not abuse, please."""
#     if isinstance(ctx.channel, discord.DMChannel):
#         await ctx.send("⚠️  You can only execute this command in a server (to prevent abuse)")
#         return
#     if ctx.author.guild_permissions.administrator:
#         output("User " + str(ctx.author.name) + " (ID: " + str(ctx.author.id) + ") from guild " + str(ctx.guild.id) + " has initiated a recache.")
#         await ctx.message.add_reaction(emoji="🔄")
#         bot.loop.create_task(cache(callback_channel=ctx.channel))
#     else:
#         await ctx.send("⚠️  Insufficient permissions, you need to have the admin permission!")

def get_member_count() -> int:
    counter = 0
    for guild in bot.guilds:
        for _ in guild.members:
            counter += 1
    return counter


@bot.command()
async def stats(ctx):
    """Returns a nice embed with neat statistics of the bot :)"""
    current_time = time.time()
    difference = int(round(current_time - start_time))
    text = str(datetime.timedelta(seconds=difference))
    embed = discord.Embed(title="Stats", description="Stats for EasyRoles", color=discord.Color.gold())
    embed.add_field(name="Uptime", value=text, inline=True)
    embed.add_field(name="Server Count", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Member Count", value=str(get_member_count()), inline=True)
    embed.add_field(name="Roles given since start", value=str(stats_roles_given), inline=True)
    embed.add_field(name="Roles revoked since start", value=str(stats_roles_revoked), inline=True)
    await ctx.send(embed=embed)


@bot.command()
@commands.cooldown(25, 180, commands.BucketType.guild)
async def selfrole(ctx, *, args):
    """Sends a message to the current chat the users can react to with 👍 (default) to get the role.
    Arguments:
        -m (Mention, required)
        -e (Custom Emoji, optional)
        --msg (Custom Message, optional)

    **NOTE**: A custom message has to be wrapped in quotation marks if it contains spaces!
    Has a cooldown of 25 executions every three minutes per guild. Do not abuse, please.
    """
    global cached_selfrole_msgs

    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("⚠️  You can only execute this command in a server!")
        return

    args = shlex.split(args)
    options = {k: True if v.startswith('-') else v
               for k, v in zip(args, args[1:] + ["--"]) if k.startswith('-')}

    message = "Click on {emoji} below this message to get the role {mention}"
    emoji = "👍"
    if "--msg" in options.keys():
        message = options["--msg"]
    if "-e" in options.keys():
        emoji = options["-e"]
    if "-m" not in options.keys():
        await ctx.send("⚠️  You have to specify a role mention with the parameter -m!")
        return
    mention = options["-m"]
    mention = str(mention)
    if ctx.author.guild_permissions.administrator:
        try:
            await ctx.message.delete()
        except:
            pass
        msg = await ctx.send(message.replace("{mention}", mention).replace("{emoji}", emoji))
        await msg.add_reaction(emoji)
        db.collection(str(ctx.channel.id)).document(str(msg.id)).set({
            "message": message,
            "emoji": emoji,
            "mention_id": mention[3:len(mention) - 1]
        })
        cached_selfrole_msgs.append({"channel_id": ctx.channel.id, "message_id": msg.id, "mention_id": mention[3:len(mention) - 1], "emoji": emoji})
        output("-> Added selfroling message with ID" + str(msg.id) + " to cache with channel ID " + str(ctx.channel.id))
    else:
        await ctx.send("⚠️  Insufficient permissions, you need to have the admin permission!")


@bot.command(aliases=["config"])
@commands.cooldown(3, 10, commands.BucketType.guild)
async def flag(ctx, option_to_change=None, value=None):
    """Allows you to change a server-specific flag. Enter the command without arguments to see the available flags and values.
        Has a cooldown of 10 executions every three minutes per guild. Do not abuse, please.
    """
    global cached_config_options  # ugly, ik
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("⚠️  You can only execute this command in a server!")
        return
    if ctx.author.guild_permissions.administrator:
        if option_to_change is not None and value is not None:
            value = str(value).lower()
            if not config.has_section(str(ctx.guild.id)):
                config.add_section(str(ctx.guild.id))
            if option_to_change in available_options_and_values.keys():
                if value in available_options_and_values[option_to_change]:
                    try:
                        db.collection("guild_config").document(str(ctx.guild.id)).set({
                            option_to_change: value
                        }, merge=True)

                    except Exception as e:
                        output(e)
                        await ctx.send("⚠️  Couldn't set this flag, please check log :(")
                    else:
                        for cached_config_option in cached_config_options:
                            if cached_config_option["guild_id"] == str(ctx.guild.id):
                                cached_config_option[option_to_change] = value  # changing the cached config for this guild :)
                        await ctx.send(
                            "✅  Flag `" + option_to_change + "` successfully changed to `" + value + "` for this guild :)")
                else:
                    await ctx.send("⚠️  Invalid value for flag `" + option_to_change + "`. Available values: " + str(
                        available_options_and_values[option_to_change]))
            else:
                await ctx.send("⚠️  Invalid flag. Available: \n```" + str(available_options_and_values) + "```")
        else:
            await ctx.send("⚠️  Usage: `" + prefix + "flag flag_to_change new_value`. Available flags/values: \n```" + str(
                available_options_and_values) + "```")
    else:
        await ctx.send("⚠️  Insufficient permissions, you need to have the admin permission in this server!")


@bot.event
async def on_raw_reaction_add(reaction):
    """Adds role to user when they react to the self role message AND removes existing roles IN CASE the replace_existing_roles option is set to "true". """
    global stats_roles_given, stats_roles_revoked
    user = reaction.member
    message = await bot.get_channel(reaction.channel_id).fetch_message(reaction.message_id)
    channel = bot.get_channel(reaction.channel_id)

    cached_selfrole_message = next((item for item in cached_selfrole_msgs if str(item["channel_id"]) == str(channel.id) and str(item["message_id"]) == str(message.id)), None)
    cached_config_option = next((item for item in cached_config_options if str(item["guild_id"]) == str(message.guild.id)), None)

    if user.id != bot.user.id:
        if not cached_selfrole_message:
            values = None
        else:
            values = cached_selfrole_message

        if values is not None:
            if reaction.emoji == values["emoji"]:
                if cached_config_option and "replace_existing_roles" in cached_config_option and (cached_config_option["replace_existing_roles"] == "true" or cached_config_option["replace_existing_roles"] is True):
                    for role_i in user.roles:
                        try:
                            if role_i.name != "@everyone":
                                await user.remove_roles(role_i)
                                stats_roles_revoked += 1
                        except:
                            pass

                role_o = message.guild.get_role(int(values["mention_id"]))
                await user.add_roles(role_o)
                stats_roles_given += 1
                output("User " + user.name + " acquired role " + role_o.name + ".")
        # else:
            # Do nothing because the reaction is none of our business :)


@bot.event
async def on_raw_reaction_remove(reaction):
    """Removes the corresponding role when the user removes their reaction from the self role message"""
    global stats_roles_revoked
    user = bot.get_guild(reaction.guild_id).get_member(reaction.user_id)
    message = await bot.get_channel(reaction.channel_id).fetch_message(reaction.message_id)
    channel = bot.get_channel(reaction.channel_id)

    cached_selfrole_message = next((item for item in cached_selfrole_msgs if str(item["channel_id"]) == str(channel.id) and str(item["message_id"]) == str(message.id)), None)

    if cached_selfrole_message:
        values = cached_selfrole_message
        role_o = message.guild.get_role(int(values["mention_id"]))
        await user.remove_roles(role_o)
        stats_roles_revoked += 1
        output("User " + user.name + " revoked role " + role_o.name + ".")


@selfrole.error
@flag.error
# @recache.error
async def selfrole_cmd_error_handler(ctx, error):
    await ctx.send("Oh no! An error ocurred:\nError: `" + str(error) + "`")
    output(error)

bot.loop.create_task(status_task())
bot.loop.create_task(cache())
bot.run(config["bot"]["token"])
