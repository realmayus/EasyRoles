import asyncio
from typing import List

import discord.ui
from discord import SelectOption, InteractionMessage


class Select(discord.ui.Select):
    def __init__(self, roles: List[discord.Role], bot: discord.Client, message: discord.Message, callback, existing_role_providers):
        self.bot = bot
        self.message = message
        self.on_finish_callback = callback
        self.existing_role_providers = existing_role_providers

        print(len(roles), ",".join([str(r) for r in roles]))

        options = [SelectOption(label=role.name, value=str(role.id)) for role in roles]
        super().__init__(placeholder="Select a role", max_values=1, min_values=1, options=options)

    def is_valid_emoji(self, reaction: discord.Reaction, user: discord.User, interaction: discord.Interaction, msg: InteractionMessage) -> bool:
        return user == interaction.user and msg.id == reaction.message.id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(int(self.values[0]))
        if role.id in [i["mention_id"] for i in self.existing_role_providers]:
            return await interaction.message.edit(content="❌  | This role already has a role provider attached to this message.", delete_after=5)


        await interaction.message.edit(content=f"Got it. Which emoji should correspond to @{role.name}? Please **react to this message**.", view=None)

        while True:
            try:
                reaction, _ = await self.bot.wait_for("reaction_add", check=lambda re, user: self.is_valid_emoji(re, user, interaction, interaction.message), timeout=60)
            except asyncio.TimeoutError:
                await interaction.message.edit(content="❌  | You took too long to react.", delete_after=5)
            else:
                await interaction.message.clear_reactions()
                if not isinstance(reaction.emoji, str) and not reaction.emoji.is_usable():
                    await interaction.message.edit(content=f"❌  | I can't use this emoji. Please choose another one.")
                else:
                    break

        if reaction.emoji in [i["emoji"] for i in self.existing_role_providers]:
            return await interaction.message.edit(content="❌  | This message already has role providers with this emoji.", delete_after=5)

        await interaction.message.edit(content=f"✅  | Done! You selected the role @{role.name} and {reaction.emoji} as the emoji.", delete_after=5)
        await self.on_finish_callback(reaction.emoji, role, self.message)


class AddRoleProvider(discord.ui.View):

    def __init__(self, roles: List[discord.Role], bot: discord.Client, message, callback, existing_role_providers):
        super().__init__()
        self.role = Select(roles, bot, message, callback, existing_role_providers)
        self.add_item(self.role)
