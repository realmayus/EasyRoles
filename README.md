# EasyRoles
A really simple reaction-based self role bot for Discord, written in Python.

It allows you to have the bot send a message that your server's members can react to. If they do this, the bot will give them the specified role.

## How to use / Commands
EasyRoles' commands have the prefix `::` by default.
### ::help
Shows a useful help section. Provide the command you need help for as a second argument if you want.

### ::selfrole
Initiate a self role system. 
Arguments:

 1 : *rolemention*:  A @mention of the role you want to create the selfroling system for.
 
 2 - ∞ : *msg*:  *OPTIONAL* You can define a custom message here, if not specified, it defaults to: *Click on :thumbsup: below this message to get the role {mention}*. You can use the placeholder `{mention}` for the role mention.

**Examples**:

*using default message*: `::selfrole @JapaneseSpeakers`

*with custom message*: `::selfrole @JapaneseSpeakers React with :thumbsup: below so that you can get that sweet {mention} role!`


### ::delselfrole
Remove a selfrole listener and the message. This is not neccessary, you can just delete the message by yourself but it can make the bot on your server a bit faster.
Arguments:
 1 : *channel_id*: The ID of the channel the message you want to delete is in.
 2 : *message_id*: The ID of the message you want to delete.
You can get the IDs by enabling Developer mode in Discord and rightclicking on the channel or the message.
 
### ::config
Allows you to change server-specific config values.
Arguments:
*When entered with no arguments, it will display all available config values.*
Enter in the format `::config option_to_change value`
 
## Host it by yourself
1. [Obtain a bot token](https://github.com/Chikachi/DiscordIntegration/wiki/How-to-get-a-token-and-channel-ID-for-Discord#create-an-application-in-discords-system)
2. Create a config file called `config.ini` in the same directory as the script.
3. Add the following content:

```ini
[bot]
token = $YOUR_BOT_TOKEN$
```
4. Start script and invite your bot using the URL that discord provides in the OAuth Section when you activate the "bot" checkbox.

### Use a custom prefix
If there are other bots in your server that are conflicting with EasyRoles' prefix, you may want to change it. To do that, just specify the following option in the `[bot]` section in your `config.ini` file:

```ini
prefix = ! ;where ! can be whatever character you want
```
