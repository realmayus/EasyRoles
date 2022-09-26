import asyncio
import configparser
import datetime
import time
from typing import List

import discord
import firebase_admin
from discord import app_commands, Intents
from discord.ext import commands
from discord.ext.commands import Context, Bot, when_mentioned_or
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import ArrayUnion, ArrayRemove

from AddRoleProvider import AddRoleProvider
from RemoveRoleProvider import RemoveRoleProvider


class EasyRoles(commands.Cog):
    def __init__(self, config, bot):
        self.bot = bot
        self.start_time = time.time()
        self.stats_roles_given = 0
        self.stats_roles_revoked = 0
        self.available_flags = {
            "replace_existing_roles": ["false", "true"]
        }
        firebase_cred = credentials.Certificate("firebase-sdk.json")  # Obtaining certificate from ./firebase-sdk.json
        firebase_admin.initialize_app(firebase_cred)  # Initializing firebase app with credentials
        self.db = firestore.client()
        self.cached_config_options = []
        self.cached_selfrole_msgs = []
        self.cached_uninteresting_channels = []  # The bot lazy cached these channels at some point and couldn't find a relevant role provider.
        self.config = config

        self.add_ctx_menu = app_commands.ContextMenu(
            name="Add Role Provider",
            callback=self.add_role_ctx_menu,
        )
        self.remove_ctx_menu = app_commands.ContextMenu(
            name="Remove Select Role Providers",
            callback=self.remove_ctx_menu,
        )
        self.bot.tree.add_command(self.add_ctx_menu)
        self.bot.tree.add_command(self.remove_ctx_menu)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot logged in as " + str(self.bot.user))

    async def add_role_ctx_menu(self, interaction: discord.Interaction, message: discord.Message) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("🚫  | You aren't authorized")

        if not interaction.guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌  | Please make sure that I have the 'manage roles' permission.")

        roles = []
        omitted = []
        for role in message.guild.roles:
            if role.position > interaction.guild.me.top_role.position:
                omitted.append(role.name)
                continue
            if role.is_bot_managed():
                continue
            if role.is_default():
                continue

            roles.append(role)

        if len(roles) == 0 and len(omitted) == 0:
            return await interaction.response.send_message(
                "❌  | No roles found. Please add some roles first.")
        elif len(roles) == 0:
            return await interaction.response.send_message(
                f"❌  | No viable roles found. Please add some roles first. (Roles that have been omitted due to my "
                f"role being below these: {', '.join(omitted)})")

        existing_role_providers = await self.get_role_provider(message.channel.id, message.id, None)
        if existing_role_providers is None:
            existing_role_providers = []


        await interaction.response.send_message("Okay, so you want to attach a role provider to this message? Cool, "
                                                "first select which role I should be giving to people." + (
                                                    "\n\n**Note:** The following roles have been omitted because my "
                                                    "highest role is below these: " + ", ".join(
                                                        omitted) if len(omitted) > 0 else ""),
                                                view=AddRoleProvider(roles, self.bot, message,
                                                                     self.on_finish_add_dialog, existing_role_providers))

    async def on_finish_add_dialog(self, emoji: discord.Emoji, role: discord.Role, message: discord.Message):
        await message.add_reaction(emoji)
        doc_ref = self.db.collection(str(message.channel.id)).document(str(message.id))
        if not doc_ref.get().exists:
            doc_ref.set({
                "roles": [{
                    "message": message.content,
                    "emoji": str(emoji),
                    "mention_id": role.id
                }]
            })
        else:
            doc_ref.update({
                "roles": ArrayUnion([{
                    "message": message.content,
                    "emoji": str(emoji),
                    "mention_id": role.id
                }])
            })

        if message.channel.id in self.cached_uninteresting_channels:
            self.cached_uninteresting_channels.remove(message.channel.id)
        self.cached_selfrole_msgs.append(
            {"channel_id": message.channel.id, "message_id": message.id, "mention_id": role.id,
             "emoji": emoji, "message": message.content})
        print(f"-> Added selfroling message with ID {message.id} to cache with channel ID {message.channel.id} and "
              f"emoji {emoji}")

    @commands.command(name="sync")
    async def sync(self, ctx: Context):
        if ctx.author.id != 218444620051251200:
            return await ctx.send("🚫  | You aren't authorized")

        await self.bot.tree.sync()
        await ctx.reply("Aight!")

    @commands.command(name="lookup")
    async def lookup(self, ctx: Context, server_id: int):
        if ctx.author.id != 218444620051251200:
            return await ctx.send("🚫  | You aren't authorized")

        self.bot: Bot
        channels = self.bot.get_guild(server_id).channels
        await ctx.send(f"Found {len(channels)} channels in guild {server_id}:\n\n" + "\n".join([f"- {x.name}  (`{x.id}`)" for x in channels]))


    async def lazy_cache(self, channel_id: int):
        print("Lazy-caching channel " + str(channel_id))
        msg_docs = self.db.collection(str(channel_id)).stream()
        for msg_doc in msg_docs:
            if msg_doc.exists:  # check if message is registered selfrole message
                values = msg_doc.to_dict()
                for role in values["roles"]:
                    self.cached_selfrole_msgs.append(
                        {"channel_id": channel_id, "message_id": int(msg_doc.id), "mention_id": int(role["mention_id"]),
                         "emoji": str(role["emoji"]),
                         "message": role["message"]})  # add the message from the DB to our cache

    def scout_cache(self, channel_id, message_id, emoji=None):
        """If no emoji is provided, all role providers of a message are returned"""

        results = []
        for item in self.cached_selfrole_msgs:
            if str(item["channel_id"]) == str(channel_id) and str(
                    item["message_id"]) == str(
                message_id) and (emoji == item["emoji"] if emoji is not None else True):
                results.append(item)

        if len(results) > 0:
            return results[0] if emoji is not None else results
        else:
            return None

    async def get_role_provider(self, channel_id: int, message_id: int, emoji: str = None):
        """If no emoji is provided, all role providers of a message are returned"""
        if channel_id in self.cached_uninteresting_channels:
            return None

        cached_selfrole_message = self.scout_cache(channel_id, message_id, emoji)

        if cached_selfrole_message is None:  # We need to lazy-cache that!
            await self.lazy_cache(channel_id)
            cached_selfrole_message = self.scout_cache(channel_id, message_id, emoji)

            if cached_selfrole_message is None:  # if it still is None then skip this event
                self.cached_uninteresting_channels.append(channel_id)
                print(f"-> Confirmed channel {channel_id} to be uninteresting")
                return None

        return cached_selfrole_message

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction: discord.RawReactionActionEvent):
        """Adds role to user when they react to the self role message AND removes existing roles IN CASE the
        replace_existing_roles option is set to "true". """

        channel_id = reaction.channel_id
        message_id = reaction.message_id

        cached_selfrole_message = await self.get_role_provider(channel_id, message_id, str(reaction.emoji))

        cached_config_option = next(
            (item for item in self.cached_config_options if str(item["guild_id"]) == str(reaction.guild_id)), None)

        if reaction.user_id != self.bot.user.id:
            values = cached_selfrole_message

            if values is not None:
                if str(reaction.emoji) == values["emoji"]:
                    guild = self.bot.get_guild(reaction.guild_id)

                    user = await guild.fetch_member(reaction.user_id)

                    if cached_config_option and "replace_existing_roles" in cached_config_option and (
                            cached_config_option["replace_existing_roles"] == "true" or cached_config_option[
                        "replace_existing_roles"] is True):

                        for role_i in user.roles:
                            try:
                                if role_i.name != "@everyone":
                                    await user.remove_roles(role_i)
                                    self.stats_roles_revoked += 1
                            except:
                                pass

                    await user.add_roles(discord.Object(id=int(values["mention_id"])))
                    self.stats_roles_given += 1

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, reaction):
        """Removes the corresponding role when the user removes their reaction from the self role message"""

        channel_id = reaction.channel_id
        message_id = reaction.message_id

        cached_selfrole_message = await self.get_role_provider(channel_id, message_id, str(reaction.emoji))

        if reaction.user_id != self.bot.user.id:
            values = cached_selfrole_message
            if values is not None:
                if str(reaction.emoji) == values["emoji"]:
                    guild = self.bot.get_guild(reaction.guild_id)
                    user = await guild.fetch_member(reaction.user_id)
                    await user.remove_roles(discord.Object(id=int(values["mention_id"])))
                    self.stats_roles_revoked += 1

    async def remove_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("🚫  | You aren't authorized")

        role_providers = await self.get_role_provider(message.channel.id, message.id, None)
        if role_providers is None:
            return await interaction.response.send_message("❌  | This message does not have any role providers.")

        await interaction.response.send_message("📝  | Please select the role providers which you want to be removed:",
                                                view=RemoveRoleProvider(interaction, message, role_providers,
                                                                        self.on_finish_remove_dialog))

    async def on_finish_remove_dialog(self, role_providers, selected_role_ids: List[int], message: discord.Message):

        to_remove = [r for r in role_providers if
                     r["message_id"] == message.id and r["mention_id"] in selected_role_ids]
        self.cached_selfrole_msgs = [x for x in
                                     self.cached_selfrole_msgs if x["message_id"] == message.id and x[
                                         "channel_id"] == message.channel.id and x[
                                         "mention_id"] not in selected_role_ids]
        for remove in to_remove:
            self.db.collection(str(message.channel.id)).document(str(message.id)).update({"roles": ArrayRemove(
                [{"emoji": remove["emoji"], "mention_id": remove["mention_id"], "message": remove["message"]}])})
            try:
                await message.remove_reaction(emoji=remove["emoji"], member=self.bot.user)
            except:
                pass

        print(f"Removed {len(to_remove)} role providers from message {message.id} in channel {message.channel.id}")

    @app_commands.command()
    async def stats(self, interaction: discord.Interaction):
        """Returns a nice embed with neat statistics of the bot :)"""
        current_time = time.time()
        difference = int(round(current_time - self.start_time))
        text = str(datetime.timedelta(seconds=difference))
        embed = discord.Embed(title="Stats", description="Stats for EasyRoles", color=discord.Color.gold())
        embed.add_field(name="Uptime", value=text, inline=True)
        embed.add_field(name="Server Count", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Roles given since start", value=str(self.stats_roles_given), inline=True)
        embed.add_field(name="Roles revoked since start", value=str(self.stats_roles_revoked), inline=True)
        members = 0
        for _ in self.bot.guilds:
            members += _.member_count

        top_guilds = sorted(self.bot.guilds, key=lambda d: d.member_count, reverse=True)

        embed.add_field(name="Total Members", value=str(members), inline=True)

        top_guilds_string = ""
        for i in range(min(10, len(self.bot.guilds))):
            top_guilds_string += f"{i+1}: {top_guilds[i].name} ({top_guilds[i].member_count})\n"

        await interaction.response.send_message(f"**Top guilds**:\n{top_guilds_string}", embed=embed)

    @app_commands.command()
    @app_commands.describe(
        option="The option you want to change.",
        value="The value you want to set the option to."
    )
    async def flag(self, interaction: discord.Interaction, option: str, value: str):
        """Allows you to change a server-specific flag"""
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message("⚠️  You can only execute this command in a server!")
            return
        if interaction.user.guild_permissions.administrator:
            if option is not None and value is not None:
                value = str(value).lower()
                if not self.config.has_section(str(interaction.guild.id)):
                    self.config.add_section(str(interaction.guild.id))
                if option in self.available_flags.keys():
                    if value in self.available_flags[option]:
                        try:
                            self.db.collection("guild_config").document(str(interaction.guild.id)).set({
                                option: value
                            }, merge=True)

                        except Exception as e:
                            print(e)
                            await interaction.response.send_message("⚠️  Couldn't set this flag, please check log :(")
                        else:
                            for cached_config_option in self.cached_config_options:
                                if cached_config_option["guild_id"] == str(interaction.guild.id):
                                    cached_config_option[
                                        option] = value  # changing the cached config for this guild :)
                            await interaction.response.send_message(
                                "✅  Flag `" + option + "` successfully changed to `" + value + "` for this guild :)")
                    else:
                        await interaction.response.send_message(
                            "⚠️  Invalid value for flag `" + option + "`. Available values: " + str(
                                self.available_flags[option]))
                else:
                    await interaction.response.send_message(
                        "⚠️  Invalid flag. Available: \n```" + str(self.available_flags) + "```")
            else:
                await interaction.response.send_message(
                    "⚠️  Usage: `::flag flag_to_change new_value`. Available flags/values: \n```" + str(
                        self.available_flags) + "```")
        else:
            await interaction.response.send_message(
                "⚠️  Insufficient permissions, you need to have the admin permission in this server!")

    @flag.autocomplete("option")
    async def flag_option_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=option, value=option) for option in self.available_flags.keys() if
                current.lower() in option.lower()]

    @flag.autocomplete("value")
    async def flag_value_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=value, value=value) for value in
                self.available_flags[interaction.namespace.option] if
                current.lower() in value.lower()]

    @app_commands.command()
    async def help(self, interaction):
        await interaction.response.send_message(f"Hello! I'm EasyRoles, a bot that allows your server members to assign "
                                       f"themselves roles through reactions. \nMaybe you've been a user before and "
                                       f"wonder what happened? With discord's recent API reform, I moved EasyRoles to "
                                       f"Slash Commands.\n\nIn order to add a selfrole/role provider, simply right "
                                       f"click a message and choose Apps>Add Reaction Provider, and follow the steps "
                                       f"as instructed. \n\nIf you still need help, feel free to ask on my discord "
                                       f""
                                       f"server: https://discord.gg/Q2QKtVp7rB")

_config = configparser.RawConfigParser()
_config.read("config.ini")

intent = Intents.default()
_bot = commands.Bot(command_prefix=when_mentioned_or("::"), intents=intent)
instance = EasyRoles(_config, _bot)


async def main():
    await _bot.add_cog(instance)


asyncio.run(main())
_bot.run(token=_config["bot"]["token"])
