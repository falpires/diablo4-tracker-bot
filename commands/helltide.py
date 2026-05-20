import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from maps.generator import generate_helltide_map
from maps.zones import get_helltide_zone
from utils.formatters import helltide_embed


class HelltideCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="helltide", description="Current Helltide status and zone map")
    async def helltide(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await fetch_events()
        ht = data.get("helltide", {})
        ts_ms = ht.get("time", 0)
        zone = get_helltide_zone(ts_ms) if ts_ms else None

        embed = helltide_embed(
            {"time": ts_ms, "chestRespawn": data.get("chestRespawn", 0)},
            zone,
        )

        map_buf = generate_helltide_map(zone)
        if map_buf:
            file = discord.File(map_buf, filename="helltide_map.png")
            embed.set_image(url="attachment://helltide_map.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelltideCog(bot))
