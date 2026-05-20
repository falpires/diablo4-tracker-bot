import time
import discord
from discord import app_commands
from discord.ext import commands

from maps.generator import generate_boss_map
from maps.zones import get_boss_spawn
from utils.formatters import worldboss_embed


class WorldBossCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="worldboss", description="Current World Boss status and spawn map")
    async def worldboss(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        now_ms = int(time.time() * 1000)
        boss, zones, spawn_ms, next_boss, next_zones, next_spawn_ms = get_boss_spawn(now_ms)

        embed = worldboss_embed(boss, spawn_ms, zones, next_boss, next_spawn_ms, next_zones)

        map_buf = generate_boss_map(zones[0] if zones else None)
        if map_buf:
            file = discord.File(map_buf, filename="boss_map.png")
            embed.set_image(url="attachment://boss_map.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WorldBossCog(bot))
