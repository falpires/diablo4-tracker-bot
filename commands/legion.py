import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from utils.formatters import legion_embed


class LegionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="legion", description="Current Legion / Zone Event status")
    async def legion(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await fetch_events()
        embed = legion_embed(data)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LegionCog(bot))
