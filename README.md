# EasyRoles
A really simple reaction-based self role bot for Discord, written in Python.

It allows you to have the bot send a message that your server's members can react to. If they do this, the bot will give them the specified role.

**Invite Link**: [\<Click here to invite me\>](https://discord.com/api/oauth2/authorize?client_id=710438395830206485&permissions=8&scope=bot)

(EasyRoles needs Administrator privileges. **It only works if** the role it should give a user is **below EasyRoles's role** (i.e. EasyRoles's role must be above the roles you want to offer your members))

**Support**: https://discord.gg/53FQpTQ


## How to use / Commands
EasyRoles' commands have the prefix `::` by default.
### ::help
::help \<command\>

Shows a useful help section which contains everything in this readme, nicely organized. Provide the command you need help for as a second argument if you want.

### ::selfrole
::selfrole \<args\>

Sends a message to the current chat the users can react to with :thumbsup: (default) to get the role.

Arguments:
```
-m (Mention, required)
-e (Custom Emoji, optional)
--msg (Custom Message, optional)
```
Has a cooldown of 25 executions every three minutes per guild. Do not abuse, please.

### ::flag
::flag \[option_to_change\] \[value\]

Allows you to change a server-specific flag. Enter the command without arguments to see the available flags and values.
Has a cooldown of 10 executions every three minutes per guild. Do not abuse, please.

### ::inviteme
::inviteme 

Sends an invite link to the chat so that you can invite the bot to your server! There's a flag to have the bot send the invite via DM if you don't want to have it posted in your server.

### ::recache
::recache 

Reloads the cache for every server. Useful if things don't work as they should. Has a cooldown of 20 minutes per guild. Do not abuse, please.

## Host it by yourself
You can host EasyRoles by yourself, but it requires you to set up a (free) Firebase Firestore database.

- [Obtain a bot token](https://github.com/Chikachi/DiscordIntegration/wiki/How-to-get-a-token-and-channel-ID-for-Discord#create-an-application-in-discords-system)
- Create a config file called `config.ini` in the same directory as the script.
- Add the following content:

```ini
[bot]
token = $YOUR_BOT_TOKEN$
```
- Create a Firestore at Firebase and download the SDK certificate (see below). Save it as `firebase-sdk.json` in the same folder as the python script.
- Start script and invite your bot using this link:

Replace $YOUR_CLIENT_ID$ with the client ID provided in the dev panel:
https://discord.com/api/oauth2/authorize?client_id=$YOUR_CLIENT_ID$&permissions=8&scope=bot

### Obtain the Firebase SDK certificate
- Go to your firebase project.
- Make sure you have set up a **Firestore** database. It has to be Firestore, a realtime database is not supported.
- Go to your project's settings: ![](https://i.imgur.com/zdXgxX0.png)
- Open the `Service accounts` tab: ![](https://i.imgur.com/qMB9cFq.png)
- Click on the `Firebase Admin SDK` tab on the left and then on `Generate new private key`. Download the json file and save it in EasyRoles's directory with the file name `firebase-sdk.json`: ![](https://i.imgur.com/Xqi1kWT.png)


### Use a custom prefix
If there are other bots in your server that are conflicting with EasyRoles' prefix, you may want to change it. To do that, just specify the following option in the `[bot]` section in your `config.ini` file:

```ini
prefix = ! ;where ! can be whatever character you want
```

### Docker
1. Create a local secrets directory (here we use `$HOME/secrets/easyroles`)
2. Add `config.ini` and `firebase-sdk.json` to this directory (create as described above)
3. Clone the repo: `git clone https://github.com/realmayus/easyroles`
4. Build the docker image: `docker build --tag easyroles .`
5. Mount a secrets directory of the host to a virtual volume and run as a container: `sudo docker run -v $HOME/secrets/easyroles:/app/secrets:ro --name easyroles -d easyroles`