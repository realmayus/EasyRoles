import discord.ui
from discord import SelectOption


class Select(discord.ui.Select):

    def get_emoji(self, emoji):
        if not isinstance(emoji, str) and not emoji.is_usable():
            return "❓"
        return emoji

    def __init__(self, interaction: discord.Interaction, role_providers, set_selected):
        super().__init__()
        self.set_selected = set_selected
        self.max_values = len(role_providers)
        self.options = [SelectOption(label=interaction.guild.get_role(i["mention_id"]).name, value=i["mention_id"],
                                     emoji=self.get_emoji(i["emoji"])) for i in role_providers]

    async def callback(self, interaction: discord.Interaction):
        self.set_selected([int(i) for i in self.values])
        await interaction.response.defer()


class RemoveRoleProvider(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, message: discord.Message, role_providers, callback):
        super().__init__()
        self.message = message
        self.interaction = interaction
        self.add_item(Select(interaction, role_providers, self.set_selected))
        self.selected = []
        self.callback = callback
        self.role_providers = role_providers

    def set_selected(self, selected):
        self.selected = selected

    @discord.ui.button(label="Cancel", emoji="❌")
    async def cancel(self, interaction, item):
        await interaction.message.delete()

    @discord.ui.button(label="Okay", emoji="✅", style=discord.ButtonStyle.primary)
    async def okay(self, interaction, item):
        if len(self.selected) == 0:
            await interaction.message.reply("❌  | You didn't select any role providers to remove.", delete_after=5)
        await self.callback(self.role_providers, self.selected, self.message)
        await interaction.message.edit(content="✅  | Done!", view=None, delete_after=3)
