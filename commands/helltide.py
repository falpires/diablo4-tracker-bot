import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from api.firebase import fetch_helltide_a
from constants import HELLTIDE_DURATION_MS
from maps.generator import generate_helltide_map
from maps.zones import ZONE_ID_TO_NAME
from utils.formatters import is_active, parse_api_timestamp, dt, dt_time

EXPANSION_ZONES = {"Nahantu", "Skovos"}


def _parse_firebase(fb: dict) -> tuple[int, int, str | None]:
    """Return (start_ms, end_ms, zone_display_name) from Firebase helltide payload."""
    zone_raw = fb.get("zone")
    zone = ZONE_ID_TO_NAME.get(zone_raw, zone_raw.title() if zone_raw else None)
    start_raw = fb.get("startTime") or fb.get("id")
    end_raw = fb.get("endTime")
    start_ms = parse_api_timestamp(start_raw)
    end_ms = parse_api_timestamp(end_raw) if end_raw else start_ms + HELLTIDE_DURATION_MS
    return start_ms, end_ms, zone


class HelltideCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="helltide", description="Current Helltide status and zone map")
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    async def helltide(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        fb, data = await asyncio.gather(
            fetch_helltide_a(),
            fetch_events(),
            return_exceptions=True,
        )
        if isinstance(fb, Exception):
            fb = None
        if isinstance(data, Exception):
            data = {}

        if fb is None and not data:
            await interaction.followup.send("⚠️ Unable to fetch Helltide data. Try again shortly.", ephemeral=True)
            return

        now_ms = int(time.time() * 1000)
        chest_ms = data.get("chestRespawn", 0) if isinstance(data, dict) else 0

        if fb and isinstance(fb, dict):
            start_ms, end_ms, zone = _parse_firebase(fb)
            active = start_ms <= now_ms <= end_ms
        else:
            # Fallback: use diablo4.life time
            ht = data.get("helltide", {}) if isinstance(data, dict) else {}
            next_ms = ht.get("time", 0)
            from maps.zones import HELLTIDE_CYCLE_MS, get_helltide_zone
            prev_ms = next_ms - HELLTIDE_CYCLE_MS
            start_ms = prev_ms if is_active(prev_ms, HELLTIDE_DURATION_MS) else next_ms
            end_ms = start_ms + HELLTIDE_DURATION_MS
            zone = get_helltide_zone(start_ms) if start_ms else None
            active = is_active(start_ms, HELLTIDE_DURATION_MS)

        if active:
            desc = f"**Active** — ends {dt(end_ms)} ({dt_time(end_ms)})"
            color = discord.Color.from_rgb(180, 30, 30)
        else:
            desc = f"Starts {dt(start_ms)} ({dt_time(start_ms)})"
            color = discord.Color.from_rgb(80, 80, 80)

        embed = discord.Embed(title="🔥 Helltide", description=desc, color=color)
        if zone:
            embed.add_field(name="Zone", value=zone, inline=True)
        if chest_ms:
            embed.add_field(name="Chest Respawn", value=f"{dt(chest_ms)} ({dt_time(chest_ms)})", inline=True)

        # Expansion zone → second concurrent helltide in base zones
        if zone and zone.lower() in {z.lower() for z in EXPANSION_ZONES} and active:
            embed.add_field(
                name="🔥 Second Helltide (base zones)",
                value="Also active — check in-game for zone",
                inline=False,
            )

        embed.set_footer(text="helltides.com")

        map_buf = generate_helltide_map(zone)
        if map_buf:
            file = discord.File(map_buf, filename="helltide_map.png")
            embed.set_image(url="attachment://helltide_map.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Slow down! Try again in {error.retry_after:.0f}s.", ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelltideCog(bot))
