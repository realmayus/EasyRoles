import asyncio
import configparser
import datetime
import shlex
import time

import discord
import firebase_admin
from discord.ext import commands
from firebase_admin import credentials, firestore


class EasyRoles(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.start_time = time.time()
        self.stats_roles_given = 0
        self.stats_roles_revoked = 0
        self.available_flags = {
            "replace_existing_roles": ["false", "true"],
            "forbid_invite": ["false", "true"]
        }
        firebase_cred = credentials.Certificate("firebase-sdk.json")  # Obtaining certificate from ./firebase-sdk.json
        firebase_admin.initialize_app(firebase_cred)  # Initializing firebase app with credentials
        self.db = firestore.client()
        self.cached_config_options = []
        self.cached_selfrole_msgs = []
        self.config = config

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot logged in as " + str(self.bot.user))

    async def lazy_cache(self, channel_id: int):
        print(f"Lazy-caching channel {channel_id}")
        msg_docs = self.db.collection(str(channel_id)).stream()
        for msg_doc in msg_docs:
            if msg_doc.exists:  # check if message is registered selfrole message :3
                values = msg_doc.to_dict()
                self.cached_selfrole_msgs.append(
                    {"channel_id": channel_id, "message_id": msg_doc.id, "mention_id": values["mention_id"],
                     "emoji": values["emoji"]})  # add the message from the DB to our cache ʕ•ᴥ•ʔ

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        """Adds role to user when they react to the self role message AND removes existing roles IN CASE the replace_existing_roles option is set to "true". """
        user = reaction.member
        channel = self.bot.get_channel(reaction.channel_id)
        message = await channel.fetch_message(reaction.message_id)

        cached_selfrole_message = next((item for item in self.cached_selfrole_msgs if
                                        str(item["channel_id"]) == str(channel.id) and str(item["message_id"]) == str(
                                            message.id)), None)

        if message.author.id == self.bot.user.id and cached_selfrole_message is None:  # We need to lazy-cache that!
            await self.lazy_cache(reaction.channel_id)
            cached_selfrole_message = next((item for item in self.cached_selfrole_msgs if
                                            str(item["channel_id"]) == str(channel.id) and str(
                                                item["message_id"]) == str(
                                                message.id)), None)

            if cached_selfrole_message is None:  # if it still is None then skip this event
                return

        cached_config_option = next(
            (item for item in self.cached_config_options if str(item["guild_id"]) == str(message.guild.id)), None)

        if user.id != self.bot.user.id:
            if not cached_selfrole_message:
                values = None
            else:
                values = cached_selfrole_message

            if values is not None:
                if str(reaction.emoji) == values["emoji"]:
                    if cached_config_option and "replace_existing_roles" in cached_config_option and (cached_config_option["replace_existing_roles"] == "true" or cached_config_option["replace_existing_roles"] is True):
                        for role_i in user.roles:
                            try:
                                if role_i.name != "@everyone":
                                    await user.remove_roles(role_i)
                                    self.stats_roles_revoked += 1
                            except:
                                pass

                    role_o = message.guild.get_role(int(values["mention_id"]))
                    await user.add_roles(role_o)
                    self.stats_roles_given += 1

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction):
        """Removes the corresponding role when the user removes their reaction from the self role message"""
        channel = self.bot.get_channel(reaction.channel_id)
        message = await channel.fetch_message(reaction.message_id)

        cached_selfrole_message = next((item for item in self.cached_selfrole_msgs if
                                        str(item["channel_id"]) == str(channel.id) and str(item["message_id"]) == str(
                                            message.id)), None)

        if message.author.id == self.bot.user.id and cached_selfrole_message is None:  # We need to lazy-cache that!
            await self.lazy_cache(reaction.channel_id)
            cached_selfrole_message = next((item for item in self.cached_selfrole_msgs if
                                            str(item["channel_id"]) == str(channel.id) and str(
                                                item["message_id"]) == str(
                                                message.id)), None)

            if cached_selfrole_message is None:  # if it still is None then skip this event
                return

        if cached_selfrole_message:
            values = cached_selfrole_message
            await self.bot.http.remove_role(reaction.guild_id, reaction.user_id, int(values["mention_id"]))
            self.stats_roles_revoked += 1

    async def status_task(self):
        """interactive status, changes from ::help to the credit and back"""
        await self.bot.wait_until_ready()
        while True:
            await asyncio.sleep(7 * 60)
            await self.bot.change_presence(activity=discord.Game(name="::help"))
            await asyncio.sleep(7 * 60)
            await self.bot.change_presence(activity=discord.Game(name="::inviteme"))

    @commands.command()
    async def inviteme(self, ctx):
        """Sends an invite link to the chat so that you can invite the bot to your server! There's a flag to have the bot send the invite via DM if you don't want to have it posted in your server."""
        option = next((item for item in self.cached_config_options if str(item["guild_id"]) == str(ctx.guild.id)), None)
        if option:
            if "forbid_invite" in option.keys():
                if option["forbid_invite"] == "true":
                    try:
                        await ctx.author.send(
                            "You can invite me to your server if you like what I can do! <3\n <https://discord.com/api/oauth2/authorize?client_id=710438395830206485&permissions=8&scope=bot>")
                    except discord.errors.Forbidden:
                        await ctx.send(
                            "😞  Invite links aren't allowed in here and I couldn't send you one via DM, please `allow direct messages from server members` in your privacy settings for this server.")
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


    @commands.command()
    async def stats(self, ctx):
        """Returns a nice embed with neat statistics of the bot :)"""
        current_time = time.time()
        difference = int(round(current_time - self.start_time))
        text = str(datetime.timedelta(seconds=difference))
        embed = discord.Embed(title="Stats", description="Stats for EasyRoles", color=discord.Color.gold())
        embed.add_field(name="Uptime", value=text, inline=True)
        embed.add_field(name="Server Count", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Roles given since start", value=str(self.stats_roles_given), inline=True)
        embed.add_field(name="Roles revoked since start", value=str(self.stats_roles_revoked), inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(25, 180, commands.BucketType.guild)
    async def selfrole(self, ctx, *, args):
        """Sends a message to the current chat the users can react to with 👍 (default) to get the role.
        Arguments:
            -m (Mention, required)
            -e (Custom Emoji, optional)
            --msg (Custom Message, optional)

        **NOTE**: A custom message has to be wrapped in quotation marks if it contains spaces!
        Has a cooldown of 25 executions every three minutes per guild. Do not abuse, please.
        """
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
            self.db.collection(str(ctx.channel.id)).document(str(msg.id)).set({
                "message": message,
                "emoji": emoji,
                "mention_id": mention[3:len(mention) - 1]
            })
            self.cached_selfrole_msgs.append(
                {"channel_id": ctx.channel.id, "message_id": msg.id, "mention_id": mention[3:len(mention) - 1],
                 "emoji": emoji})
            print("-> Added selfroling message with ID" + str(msg.id) + " to cache with channel ID " + str(
                ctx.channel.id))
        else:
            await ctx.send("⚠️  Insufficient permissions, you need to have the admin permission!")

    @commands.command(aliases=["config"])
    @commands.cooldown(3, 10, commands.BucketType.guild)
    async def flag(self, ctx, option_to_change=None, value=None):
        """Allows you to change a server-specific flag. Enter the command without arguments to see the available flags and values.
            Has a cooldown of 10 executions every three minutes per guild. Do not abuse, please.
        """
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("⚠️  You can only execute this command in a server!")
            return
        if ctx.author.guild_permissions.administrator:
            if option_to_change is not None and value is not None:
                value = str(value).lower()
                if not self.config.has_section(str(ctx.guild.id)):
                    self.config.add_section(str(ctx.guild.id))
                if option_to_change in self.available_flags.keys():
                    if value in self.available_flags[option_to_change]:
                        try:
                            self.db.collection("guild_config").document(str(ctx.guild.id)).set({
                                option_to_change: value
                            }, merge=True)

                        except Exception as e:
                            print(e)
                            await ctx.send("⚠️  Couldn't set this flag, please check log :(")
                        else:
                            for cached_config_option in self.cached_config_options:
                                if cached_config_option["guild_id"] == str(ctx.guild.id):
                                    cached_config_option[
                                        option_to_change] = value  # changing the cached config for this guild :)
                            await ctx.send(
                                "✅  Flag `" + option_to_change + "` successfully changed to `" + value + "` for this guild :)")
                    else:
                        await ctx.send(
                            "⚠️  Invalid value for flag `" + option_to_change + "`. Available values: " + str(
                                self.available_flags[option_to_change]))
                else:
                    await ctx.send("⚠️  Invalid flag. Available: \n```" + str(self.available_flags) + "```")
            else:
                await ctx.send(
                    "⚠️  Usage: `::flag flag_to_change new_value`. Available flags/values: \n```" + str(
                        self.available_flags) + "```")
        else:
            await ctx.send("⚠️  Insufficient permissions, you need to have the admin permission in this server!")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await ctx.send("🚫| Oh no! An error has occurred:\n`%s`" % str(error))
        print(error)


_config = configparser.RawConfigParser()
_config.read("config.ini")

_bot = commands.Bot(command_prefix="::")

instance = EasyRoles(_bot, _config)

_bot.loop.create_task(instance.status_task())
_bot.add_cog(instance)
_bot.run(_config["bot"]["token"])
