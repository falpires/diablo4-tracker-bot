import asyncio
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from api.firebase import fetch_helltide_a
from maps.generator import generate_helltide_map
from maps.zones import get_helltide_zone, HELLTIDE_CYCLE_MS
from utils.formatters import helltide_embed, is_active, HELLTIDE_DURATION_MS, dt, dt_time

EXPANSION_ZONES = {"Nahantu", "Skovos"}


def _resolve_spawn_b(next_ms: int) -> int:
    """Resolve Helltide B spawn (diablo4.life). next_ms is always NEXT spawn."""
    prev_ms = next_ms - HELLTIDE_CYCLE_MS
    if is_active(prev_ms, HELLTIDE_DURATION_MS):
        return prev_ms
    if is_active(next_ms, HELLTIDE_DURATION_MS):
        return next_ms
    return next_ms


def _parse_firebase_helltide(fb: dict) -> tuple[int, int, str | None]:
    """Return (start_ms, end_ms, zone) from Firebase helltide payload."""
    zone = fb.get("zone")
    # Firebase returns ISO strings or unix seconds (id field)
    start_raw = fb.get("startTime") or fb.get("id")
    end_raw = fb.get("endTime")
    if isinstance(start_raw, str):
        start_ms = int(datetime.fromisoformat(start_raw.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        start_ms = int(start_raw) * 1000 if start_raw else 0
    if isinstance(end_raw, str):
        end_ms = int(datetime.fromisoformat(end_raw.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        end_ms = start_ms + HELLTIDE_DURATION_MS
    return start_ms, end_ms, zone


class HelltideCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="helltide", description="Current Helltide status and zone map")
    async def helltide(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        data, fb = await asyncio.gather(
            fetch_events(),
            fetch_helltide_a(),
            return_exceptions=True,
        )
        if isinstance(data, Exception):
            data = {}
        if isinstance(fb, Exception):
            fb = None

        now_ms = int(time.time() * 1000)

        # --- Helltide A (Firebase, spawns :00 UTC) ---
        ht_a_active = False
        ht_a_zone: str | None = None
        ht_a_end_ms = 0
        ht_a_start_ms = 0
        if fb and isinstance(fb, dict):
            ht_a_start_ms, ht_a_end_ms, ht_a_zone = _parse_firebase_helltide(fb)
            ht_a_active = ht_a_start_ms <= now_ms <= ht_a_end_ms

        # --- Helltide B (diablo4.life, spawns :55 UTC) ---
        ht = data.get("helltide", {}) if isinstance(data, dict) else {}
        next_b_ms = ht.get("time", 0)
        spawn_b_ms = _resolve_spawn_b(next_b_ms) if next_b_ms else 0
        ht_b_active = is_active(spawn_b_ms, HELLTIDE_DURATION_MS) if spawn_b_ms else False
        ht_b_zone = get_helltide_zone(spawn_b_ms) if spawn_b_ms else None
        ht_b_end_ms = spawn_b_ms + HELLTIDE_DURATION_MS

        chest_ms = data.get("chestRespawn", 0) if isinstance(data, dict) else 0

        # Build embed based on what's active
        if ht_a_active and ht_b_active:
            # Both concurrent helltides running
            color = discord.Color.from_rgb(180, 30, 30)
            zones_str = f"{ht_a_zone or 'Unknown'} & {ht_b_zone or 'Unknown'}"
            end_a = dt(ht_a_end_ms)
            end_b = dt(ht_b_end_ms)
            desc = f"**Two active helltides**\n🔥 {ht_a_zone or 'Unknown'} — ends {end_a} ({dt_time(ht_a_end_ms)})\n🔥 {ht_b_zone or 'Unknown'} — ends {end_b} ({dt_time(ht_b_end_ms)})"
            embed = discord.Embed(title="🔥 Helltide", description=desc, color=color)
            if chest_ms:
                embed.add_field(name="Chest Respawn", value=f"{dt(chest_ms)} ({dt_time(chest_ms)})", inline=True)
            map_zone = ht_a_zone  # use A zone for map
        elif ht_a_active:
            end_ms = ht_a_end_ms
            desc = f"**Active** — ends {dt(end_ms)} ({dt_time(end_ms)})"
            color = discord.Color.from_rgb(180, 30, 30)
            embed = discord.Embed(title="🔥 Helltide", description=desc, color=color)
            if ht_a_zone:
                embed.add_field(name="Zone", value=ht_a_zone, inline=True)
            if chest_ms:
                embed.add_field(name="Chest Respawn", value=f"{dt(chest_ms)} ({dt_time(chest_ms)})", inline=True)
            map_zone = ht_a_zone
        elif ht_b_active:
            end_ms = ht_b_end_ms
            desc = f"**Active** — ends {dt(end_ms)} ({dt_time(end_ms)})"
            color = discord.Color.from_rgb(180, 30, 30)
            embed = discord.Embed(title="🔥 Helltide", description=desc, color=color)
            if ht_b_zone:
                embed.add_field(name="Zone", value=ht_b_zone, inline=True)
            if chest_ms:
                embed.add_field(name="Chest Respawn", value=f"{dt(chest_ms)} ({dt_time(chest_ms)})", inline=True)
            map_zone = ht_b_zone
        else:
            # Neither active — show next from Firebase if available, else diablo4.life
            if ht_a_start_ms and ht_a_start_ms > now_ms:
                next_ms = ht_a_start_ms
                next_zone = ht_a_zone
            elif spawn_b_ms:
                next_ms = spawn_b_ms
                next_zone = ht_b_zone
            else:
                next_ms = 0
                next_zone = None
            desc = f"Starts {dt(next_ms)} ({dt_time(next_ms)})" if next_ms else "No data"
            color = discord.Color.from_rgb(80, 80, 80)
            embed = discord.Embed(title="🔥 Helltide", description=desc, color=color)
            if next_zone:
                embed.add_field(name="Zone", value=next_zone, inline=True)
            map_zone = next_zone

        embed.set_footer(text="helltides.com + diablo4.life")

        map_buf = generate_helltide_map(map_zone)
        if map_buf:
            file = discord.File(map_buf, filename="helltide_map.png")
            embed.set_image(url="attachment://helltide_map.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelltideCog(bot))
