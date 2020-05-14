import asyncio
import configparser

import discord
from discord import Role, Member, client
from discord.ext import commands

config = configparser.RawConfigParser()
config.read("config.ini")

prefix = config["bot"]["prefix"] if config.has_option("bot", "prefix") else "::"

"""Setting the command prefix to the config value if it exists, else use :: as default"""
bot = commands.Bot(command_prefix=prefix)


"""Available config options"""
available_options_and_values = {
    "replace_existing_roles": ["false", "true"],
    "forbid_invite": ["false", "true"]
}


@bot.event
async def on_ready():
    """registering interactive status task"""
    bot.loop.create_task(status_task())


async def status_task():
    """interactive status, changes from ::help to the credit and back"""
    while True:
        await bot.change_presence(activity=discord.Game(name=prefix + "help"))
        await asyncio.sleep(10)
        await bot.change_presence(activity=discord.Game(name="made by marius"))
        await asyncio.sleep(15)
        await bot.change_presence(activity=discord.Game(name=str(len([s for s in bot.guilds])) + " servers"))
        await asyncio.sleep(15)
        await bot.change_presence(activity=discord.Game(name=prefix + "inviteme"))
        await asyncio.sleep(15)


@bot.command()
async def inviteme(ctx):
    if config.has_option(str(ctx.guild.id), "forbid_invite"):
        if config[str(ctx.guild.id)]["forbid_invite"] == "false":
            await ctx.send("You can invite me to your server if you like what I can do! <3\n <https://discord.com/api/oauth2/authorize?client_id=710438395830206485&permissions=8&scope=bot>")
        else:
            await ctx.send("The owner of this server has forbidden me to send you an invite link :(")
    else:
        await ctx.send("You can invite me to your server if you like what I can do! <3\n <https://discord.com/api/oauth2/authorize?client_id=710438395830206485&permissions=8&scope=bot>")


@bot.command()
async def selfrole(ctx, rolemention: Role, msg="Click on :thumbsup: below this message to get the role {mention}", *args):
    """Sends a message to the current chat the users can react to with 👍 to get the role.
    You can customize the message by passing it as arguments after the mention. You can use {mention} as a placeholder where the bot inserts the role.
    Arguments: rolemention (required), msg (optional)
    """
    msg_builder = msg
    for arg in args:
        msg_builder += " " + arg
    msg = msg_builder
    if ctx.author.guild_permissions.administrator:
        try:
            await ctx.message.delete()
        except:
            pass
        msg = await ctx.send(msg.replace("{mention}", rolemention.mention))
        await msg.add_reaction("👍")

        if not config.has_section(str(ctx.message.guild.id)):
            config.add_section(str(ctx.message.guild.id))
        config.set(str(ctx.message.guild.id), str(msg.id), str(rolemention.id))
        with open("config.ini", "w") as f:
            config.write(f)
    else:
        await ctx.send("Insufficient permissions, you need to have the admin permission!")


@bot.command()
async def delselfrole(ctx, channel_id, message_id):
    """Removes the listener for reactions on a selfrole message and deletes it.
    Arguments: channel_id, message_id (obtainable by rightclicking channel and message > copy ID (need to have dev mode enabled)"""
    if ctx.author.guild_permissions.administrator:
        try:
            await ctx.message.delete()  # remove command message
        except:
            pass
        msg = await bot.get_channel(int(channel_id)).fetch_message(int(message_id))
        await msg.delete()
        try:
            config.remove_option(str(ctx.message.guild.id), str(message_id))
            with open("config.ini", "w") as f:
                config.write(f)
        except Exception as e:
            print(e)
    else:
        await ctx.send("Insufficient permissions, you need to have the admin permission!")


@bot.command(name="config")
async def config_cmd(ctx, option_to_change=None, value=None):
    """Allows you to change a server-specific config value. Enter the command without arguments to see the available options and values."""
    if ctx.author.guild_permissions.administrator:
        if option_to_change is not None and value is not None:
            value = str(value).lower()
            if not config.has_section(str(ctx.guild.id)):
                config.add_section(str(ctx.guild.id))
            if option_to_change in available_options_and_values.keys():
                if value in available_options_and_values[option_to_change]:
                    try:
                        config.set(str(ctx.guild.id), str(option_to_change), str(value))
                        with open("config.ini", "w") as f:
                            config.write(f)
                    except Exception as e:
                        print(e)
                    finally:
                        await ctx.send("Option " + option_to_change + " changed to " + value + " successfully for this guild :)")
                else:
                    await ctx.send("Invalid value for option " + option_to_change + ". Available values: " + str(available_options_and_values[option_to_change]))
            else:
                await ctx.send("Invalid option. Available: \n```" + str(available_options_and_values) + "```")
        else:
            await ctx.send("Usage: `::config option_to_change new_value`. Available options/values: \n```" + str(available_options_and_values) + "```")
    else:
        await ctx.send("Insufficient permissions, you need to have the admin permission!")


@bot.event
async def on_raw_reaction_add(reaction):
    """Adds role to user when they react to the self role message AND removes existing roles IN CASE the replace_existing_roles option is set to "true". """
    user = reaction.member
    message = await bot.get_channel(reaction.channel_id).fetch_message(reaction.message_id)
    if reaction.emoji.name == "👍" and user.id != bot.user.id:
        if config.has_option(str(message.guild.id), str(message.id)):
            role = config[str(message.guild.id)][str(message.id)]
            if config.has_section(str(message.guild.id)) and config.has_option(str(message.guild.id), "replace_existing_roles"):
                if config[str(message.guild.id)]["replace_existing_roles"] == "true":
                    roles_to_remove = []
                    for role_i in user.roles:
                        try:
                            if role_i.name != "@everyone":
                                await user.remove_roles(role_i)
                        except:
                            pass
                        finally:
                            roles_to_remove.append(role_i)
                    for selfrole_msg_id in config[str(message.guild.id)].keys():
                        if selfrole_msg_id != str(message.id) and selfrole_msg_id not in available_options_and_values.keys():
                            selfrole_msg = await message.channel.fetch_message(selfrole_msg_id)
                            await selfrole_msg.remove_reaction("👍", user)

            role_o = message.guild.get_role(int(role))
            print("User " + user.name + " acquired role " + role_o.name + ".")
            await user.add_roles(role_o)


@bot.event
async def on_raw_reaction_remove(reaction):
    """Removes the corresponding role when the user removes their reaction from the self role message"""
    user = bot.get_guild(reaction.guild_id).get_member(reaction.user_id)
    message = await bot.get_channel(reaction.channel_id).fetch_message(reaction.message_id)
    if reaction.emoji.name == "👍" and user.id != bot.user.id:
        if config.has_option(str(reaction.guild_id), str(message.id)):
            role = config[str(reaction.guild_id)][str(message.id)]
            role_o = message.guild.get_role(int(role))
            await user.remove_roles(role_o)
            print("User " + user.name + " revoked role " + role_o.name + ".")


bot.run(config["bot"]["token"])
