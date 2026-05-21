import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from utils.formatters import legion_embed


class LegionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="legion", description="Current Legion / Zone Event status")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    async def legion(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            data = await fetch_events()
        except Exception:
            data = {}
        if not data:
            await interaction.followup.send("⚠️ Unable to fetch Legion data. Try again shortly.", ephemeral=True)
            return
        embed = legion_embed(data)
        await interaction.followup.send(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Slow down! Try again in {error.retry_after:.0f}s.", ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LegionCog(bot))
