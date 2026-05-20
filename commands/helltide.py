import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from maps.generator import generate_helltide_map
from maps.zones import get_helltide_zone, get_helltide_second_zone, HELLTIDE_CYCLE_MS
from utils.formatters import helltide_embed, is_active, HELLTIDE_DURATION_MS, dt, dt_time


def _resolve_spawn(next_ms: int) -> int:
    """Resolve the relevant spawn time from the API's next-spawn value."""
    prev_ms = next_ms - HELLTIDE_CYCLE_MS
    if is_active(prev_ms, HELLTIDE_DURATION_MS):
        return prev_ms
    if is_active(next_ms, HELLTIDE_DURATION_MS):
        return next_ms
    return next_ms


class HelltideCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="helltide", description="Current Helltide status and zone map")
    async def helltide(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await fetch_events()
        ht = data.get("helltide", {})
        next_ms = ht.get("time", 0)
        spawn_ms = _resolve_spawn(next_ms) if next_ms else 0

        zone1 = get_helltide_zone(spawn_ms) if spawn_ms else None
        zone2 = get_helltide_second_zone(spawn_ms) if spawn_ms else None

        # Build primary embed for helltide 1
        embed = helltide_embed(
            {"time": spawn_ms, "chestRespawn": data.get("chestRespawn", 0)},
            zone1,
        )

        # Add second concurrent helltide info
        if zone2 and spawn_ms:
            active2 = is_active(spawn_ms, HELLTIDE_DURATION_MS)
            if active2:
                end_ms = spawn_ms + HELLTIDE_DURATION_MS
                val2 = f"**Active** — ends {dt(end_ms)} ({dt_time(end_ms)})"
            else:
                val2 = f"Starts {dt(spawn_ms)} ({dt_time(spawn_ms)})"
            embed.add_field(name=f"🔥 Helltide 2 — {zone2}", value=val2, inline=False)

        map_buf = generate_helltide_map(zone1)
        if map_buf:
            file = discord.File(map_buf, filename="helltide_map.png")
            embed.set_image(url="attachment://helltide_map.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelltideCog(bot))
