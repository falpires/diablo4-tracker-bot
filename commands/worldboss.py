import asyncio
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from api.diablo4life import fetch_events
from api.firebase import fetch_world_boss_firebase
from maps.generator import generate_boss_map
from utils.formatters import worldboss_embed, is_active

BOSS_WINDOW_MS = 15 * 60 * 1000


def _parse_world_boss(fb: dict, d4life: dict) -> tuple[str, list[str], int, int]:
    """Return (name, zones, spawn_ms, next_spawn_ms)."""
    start_raw = fb.get("startTime") or fb.get("id")
    next_raw = fb.get("nextTime")

    if isinstance(start_raw, str):
        spawn_ms = int(datetime.fromisoformat(start_raw.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        spawn_ms = int(start_raw) * 1000 if start_raw else 0

    if isinstance(next_raw, str):
        next_spawn_ms = int(datetime.fromisoformat(next_raw.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        next_spawn_ms = spawn_ms + 12600 * 1000

    zones = [z["name"] for z in fb.get("zone", []) if z.get("name")]

    # Use d4life name if its timestamp matches Firebase slot (more accurate name)
    d4_name = d4life.get("name", "")
    d4_time = d4life.get("time", 0)
    if d4_name and d4_time and d4_time == spawn_ms:
        name = d4_name
    else:
        boss_raw = fb.get("boss", "Unknown")
        name = _full_boss_name(boss_raw)

    return name, zones, spawn_ms, next_spawn_ms


def _full_boss_name(short: str) -> str:
    return {
        "Ashava": "Ashava the Pestilent",
        "Avarice": "Avarice, the Gold Cursed",
        "Wandering Death": "Wandering Death, Death Given Life",
    }.get(short, short)


class WorldBossCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="worldboss", description="Current World Boss status and spawn map")
    async def worldboss(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        fb, data = await asyncio.gather(
            fetch_world_boss_firebase(),
            fetch_events(),
            return_exceptions=True,
        )
        if isinstance(fb, Exception) or not fb:
            fb = {}
        if isinstance(data, Exception):
            data = {}

        d4_wb = data.get("worldBoss", {}) if isinstance(data, dict) else {}
        name, zones, spawn_ms, next_spawn_ms = _parse_world_boss(fb, d4_wb)

        embed = worldboss_embed(name, spawn_ms, zones, next_spawn_ms)

        map_zone = zones[0] if zones else None
        if not is_active(spawn_ms, BOSS_WINDOW_MS):
            map_zone = zones[0] if zones else None

        map_buf = generate_boss_map(map_zone)
        if map_buf:
            file = discord.File(map_buf, filename="boss_map.png")
            embed.set_image(url="attachment://boss_map.png")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WorldBossCog(bot))
